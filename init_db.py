import sqlite3
db = sqlite3.connect('community.db')
c = db.cursor()
c.executescript('''
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 username TEXT UNIQUE,
 password TEXT,
 bio TEXT
);
CREATE TABLE IF NOT EXISTS posts (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER,
 title TEXT,
 body TEXT,
 created INTEGER,
 image TEXT
);
CREATE TABLE IF NOT EXISTS comments (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 post_id INTEGER,
 user_id INTEGER,
 body TEXT,
 created INTEGER
);
CREATE TABLE IF NOT EXISTS comment_likes (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 comment_id INTEGER,
 user_id INTEGER
);
''')
db.commit()
print('Initialized community.db with extended tables')
db.close()
