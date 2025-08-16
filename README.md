# Community App - Render Ready

이 레포는 Render에서 바로 배포 가능한 상태로 구성되어 있습니다.
모든 파일이 루트에 있어 GitHub 업로드 후 Render에 연결하면 바로 배포 가능.

## Render 배포 가이드

1. Python Version: 3.11
2. Build Command:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
3. Start Command:
   ```bash
   gunicorn app:app --bind 0.0.0.0:$PORT
   ```
4. 환경 변수 설정: `SECRET_KEY` 권장

## 로컬 실행

1. 가상환경 생성/활성화
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```
2. 패키지 설치
   ```bash
   pip install -r requirements.txt
   ```
3. DB 초기화
   ```bash
   python init_db.py
   ```
4. 앱 실행
   ```bash
   python app.py
   ```

모든 기능: 회원가입, 로그인, 글 작성, 댓글, 댓글 좋아요, 이미지 업로드, 페이징 지원.
