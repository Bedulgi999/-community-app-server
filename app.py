from flask import Flask, request, redirect, url_for, session, g, send_from_directory, flash
from flask import Markup
import sqlite3, os, hashlib, hmac, time, math
from jinja2 import Template
from werkzeug.utils import secure_filename

DATABASE = 'community.db'
SECRET_KEY = os.environ.get('SECRET_KEY','dev-secret-key')
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif'}

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ROOT = os.path.dirname(os.path.abspath(__file__))

# --- Simple template loader: loads files named tpl_*.html from root ---
def render_template_from_root(name, **context):
    path = os.path.join(ROOT, f"tpl_{name}.html")
    with open(path, 'r', encoding='utf-8') as f:
        src = f.read()
    tpl = Template(src)
    return tpl.render(**context)

# --- Database helpers ---
def get_db():
    db = getattr(g, '_db', None)
    if db is None:
        db = g._db = sqlite3.connect(DATABASE, detect_types=sqlite3.PARSE_DECLTYPES)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    cur.close()

# --- Auth helpers ---
def hash_pw(pw, salt=None):
    if salt is None:
        salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + hashed.hex()

def check_pw(stored, pw):
    salt_hex, hash_hex = stored.split(':')
    salt = bytes.fromhex(salt_hex)
    h = hashlib.pbkdf2_hmac('sha256', pw.encode('utf-8'), salt, 100000)
    return h.hex() == hash_hex

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return query_db('SELECT id, username, bio FROM users WHERE id=?', (uid,), one=True)

# --- Utility ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

# --- Routes ---
@app.route('/')
def index():
    page = int(request.args.get('page',1))
    per_page = 5
    total_posts = query_db('SELECT COUNT(*) as cnt FROM posts', one=True)['cnt']
    total_pages = math.ceil(total_posts / per_page)
    offset = (page-1)*per_page
    posts = query_db('SELECT p.id, p.title, p.body, p.created, u.username FROM posts p JOIN users u ON p.user_id=u.id ORDER BY p.created DESC LIMIT ? OFFSET ?', (per_page, offset))
    return render_template_from_root('index', posts=posts, user=current_user(), page=page, total_pages=total_pages)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username = request.form['username'].strip()
        password = request.form['password']
        if not username or not password:
            return "missing fields",400
        if query_db('SELECT id FROM users WHERE username=?',(username,),one=True):
            return "username exists",400
        pw = hash_pw(password)
        execute_db('INSERT INTO users (username,password,bio) VALUES (?,?,?)',(username,pw,''))
        return redirect(url_for('login'))
    return render_template_from_root('register', user=current_user())

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form['username'].strip()
        password = request.form['password']
        u = query_db('SELECT id,password FROM users WHERE username=?',(username,),one=True)
        if not u or not check_pw(u['password'],password):
            return "invalid credentials",400
        session['user_id'] = u['id']
        return redirect(url_for('index'))
    return render_template_from_root('login', user=current_user())

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/post/new', methods=['GET','POST'])
def new_post():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    if request.method=='POST':
        title = request.form['title'][:200]
        body = request.form['body']
        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                image_filename = secure_filename(f"{int(time.time())}_{file.filename}")
                file.save(os.path.join(UPLOAD_FOLDER,image_filename))
        execute_db('INSERT INTO posts (user_id,title,body,created,image) VALUES (?,?,?,?,?)',(user['id'],title,body,int(time.time()),image_filename))
        return redirect(url_for('index'))
    return render_template_from_root('post_new', user=user)

@app.route('/post/<int:pid>', methods=['GET','POST'])
def view_post(pid):
    post = query_db('SELECT p.*, u.username FROM posts p JOIN users u ON p.user_id=u.id WHERE p.id=?',(pid,),one=True)
    if not post:
        return "not found",404
    if request.method=='POST':
        user = current_user()
        if not user:
            return redirect(url_for('login'))
        comment = request.form['comment']
        execute_db('INSERT INTO comments (post_id,user_id,body,created) VALUES (?,?,?,?)',(pid,user['id'],comment,int(time.time())))
        return redirect(url_for('view_post',pid=pid))
    comments = query_db('SELECT c.*, u.username FROM comments c JOIN users u ON c.user_id=u.id WHERE c.post_id=? ORDER BY c.created ASC',(pid,))
    # like info per comment (simple, count likes)
    likes = {c['id']: query_db('SELECT COUNT(*) as cnt FROM comment_likes WHERE comment_id=?',(c['id'],),one=True)['cnt'] for c in comments}
    return render_template_from_root('post_view', post=post, comments=comments, likes=likes, user=current_user())

@app.route('/post/<int:pid>/like_comment/<int:cid>')
def like_comment(pid,cid):
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    existing = query_db('SELECT * FROM comment_likes WHERE comment_id=? AND user_id=?',(cid,user['id']),one=True)
    if not existing:
        execute_db('INSERT INTO comment_likes (comment_id,user_id) VALUES (?,?)',(cid,user['id']))
    return redirect(url_for('view_post',pid=pid))

@app.route('/user/<username>')
def profile(username):
    u = query_db('SELECT id,username,bio FROM users WHERE username=?',(username,),one=True)
    if not u:
        return "not found",404
    posts = query_db('SELECT id,title,created FROM posts WHERE user_id=? ORDER BY created DESC',(u['id'],))
    return render_template_from_root('profile', profile=u, posts=posts, user=current_user())

@app.route('/search')
def search():
    q = request.args.get('q','').strip()
    results = []
    if q:
        qlike = f"%{q}%"
        results = query_db('SELECT id,title,created FROM posts WHERE title LIKE ? OR body LIKE ? ORDER BY created DESC LIMIT 50',(qlike,qlike))
    return render_template_from_root('search', q=q, results=results, user=current_user())

@app.route('/static/<path:filename>')
def static_root(filename):
    candidate = os.path.join(ROOT,f"static_{filename}")
    if os.path.exists(candidate):
        return send_from_directory(ROOT,f"static_{filename}")
    return "not found",404

if __name__=='__main__':
    if not os.path.exists(DATABASE):
        print("Database missing. Run: python init_db.py")
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
