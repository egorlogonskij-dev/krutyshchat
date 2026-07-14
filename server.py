from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json, os, bcrypt, aiofiles
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

app = FastAPI()

# --- База данных SQLite ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./krutysh.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    avatar = Column(String, default="default.png")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    room = Column(String)
    username = Column(String)
    text = Column(Text)
    file = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

# --- Папки для файлов ---
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# --- Хранилище активных соединений ---
active_connections = {}

# --- HTML-интерфейс (СМОТРИ НИЖЕ) ---
html = """
<!DOCTYPE html>
<html>
<head>
    <title>KRUTYSH CHAT ULTRA</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0a; color: #00ff88; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
        .container { width: 95%; max-width: 900px; background: #111; border: 2px solid #00ff88; border-radius: 20px; padding: 20px; box-shadow: 0 0 40px #00ff8844; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #00ff8855; padding-bottom: 10px; flex-wrap: wrap; gap: 10px; }
        .header h1 { font-size: 24px; text-shadow: 0 0 10px #00ff88; }
        .user-info { display: flex; align-items: center; gap: 15px; }
        .user-info img { width: 32px; height: 32px; border-radius: 50%; border: 1px solid #00ff88; }
        .logout-btn { background: #ff2244; color: white; border: none; padding: 4px 12px; border-radius: 12px; cursor: pointer; font-size: 12px; }
        .rooms { display: flex; gap: 10px; margin: 15px 0; flex-wrap: wrap; }
        .room-btn { background: #222; color: #00ff88; border: 1px solid #00ff8844; padding: 6px 18px; border-radius: 20px; cursor: pointer; }
        .room-btn.active { background: #00ff8833; border-color: #00ff88; }
        #messages { height: 400px; overflow-y: auto; padding: 10px; background: #0d0d0d; border-radius: 10px; margin: 10px 0; border: 1px solid #00ff8844; }
        .msg { margin: 6px 0; padding: 6px 10px; border-radius: 8px; background: #1a1a1a; border-left: 3px solid #00ff88; }
        .msg .user { color: #88ffaa; font-weight: bold; }
        .msg .time { color: #666; font-size: 11px; margin-left: 10px; }
        .msg .text { color: #ddd; margin-top: 4px; word-wrap: break-word; }
        .msg img { max-width: 200px; border-radius: 8px; margin-top: 4px; }
        .input-area { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
        #msgInput { flex: 1; background: #1a1a1a; color: #00ff88; border: 1px solid #00ff8855; padding: 12px; border-radius: 30px; outline: none; font-size: 16px; min-width: 150px; }
        #fileInput { display: none; }
        .action-btn { background: #222; color: #00ff88; border: 1px solid #00ff8844; padding: 10px 14px; border-radius: 30px; cursor: pointer; font-size: 18px; }
        .action-btn:hover { background: #00ff8822; }
        .sticker-picker { display: flex; gap: 8px; margin: 8px 0; flex-wrap: wrap; }
        .sticker { font-size: 28px; cursor: pointer; background: #1a1a1a; padding: 4px 10px; border-radius: 12px; transition: 0.2s; border: 1px solid transparent; }
        .sticker:hover { border-color: #00ff88; background: #00ff8811; }
        #videoContainer { margin: 10px 0; display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; }
        #videoContainer video { width: 300px; max-width: 100%; border-radius: 12px; background: #111; border: 1px solid #00ff8844; }
        .call-btn { background: #00ff88; color: #0a0a0a; border: none; padding: 6px 16px; border-radius: 20px; font-weight: bold; cursor: pointer; }
        .login-box { max-width: 400px; margin: 0 auto; padding: 40px; background: #111; border: 2px solid #00ff88; border-radius: 20px; text-align: center; }
        .login-box input { display: block; width: 100%; padding: 12px; margin: 10px 0; background: #1a1a1a; color: #00ff88; border: 1px solid #00ff8855; border-radius: 30px; }
        .login-box button { background: #00ff88; color: #0a0a0a; border: none; padding: 12px; border-radius: 30px; font-weight: bold; width: 100%; cursor: pointer; }
        .hidden { display: none; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0a0a0a; }
        ::-webkit-scrollbar-thumb { background: #00ff88; border-radius: 10px; }
    </style>
</head>
<body>
<div id="loginPage" class="login-box">
    <h2>🔐 ВХОД</h2>
    <input type="text" id="loginUsername" placeholder="Логин">
    <input type="password" id="loginPassword" placeholder="Пароль">
    <button onclick="login()">Войти</button>
    <button onclick="register()" style="background:#444;color:#00ff88;margin-top:10px;">Зарегистрироваться</button>
</div>
<div id="chatApp" class="container hidden">
    <div class="header">
        <h1>💬 KRUTYSH ULTRA</h1>
        <div class="user-info">
            <span id="currentUser"></span>
            <button class="logout-btn" onclick="logout()">Выйти</button>
        </div>
    </div>
    <div class="rooms">
        <button class="room-btn active" data-room="general">#общий</button>
        <button class="room-btn" data-room="random">#флуд</button>
        <button class="room-btn" data-room="private">#секрет</button>
    </div>
    <div id="messages"></div>
    <div class="sticker-picker">
        <span class="sticker" onclick="sendSticker('😂')">😂</span>
        <span class="sticker" onclick="sendSticker('🔥')">🔥</span>
        <span class="sticker" onclick="sendSticker('💀')">💀</span>
        <span class="sticker" onclick="sendSticker('🤖')">🤖</span>
        <span class="sticker" onclick="sendSticker('👾')">👾</span>
        <span class="sticker" onclick="sendSticker('😈')">😈</span>
    </div>
    <div class="input-area">
        <input type="text" id="msgInput" placeholder="Напиши сообщение...">
        <button class="action-btn" onclick="sendMsg()">📤</button>
        <button class="action-btn" onclick="document.getElementById('fileInput').click()">📎</button>
        <input type="file" id="fileInput" multiple accept="image/*" onchange="sendFile(this)">
        <button class="call-btn" onclick="startCall()">📹 Звонок</button>
    </div>
    <div id="videoContainer"></div>
</div>
<script>
    let ws, currentRoom = 'general', currentUser = '';

    function showApp() { document.getElementById('loginPage').classList.add('hidden'); document.getElementById('chatApp').classList.remove('hidden'); }
    function showLogin() { document.getElementById('loginPage').classList.remove('hidden'); document.getElementById('chatApp').classList.add('hidden'); }

    async function login() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const res = await fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
        if (res.ok) { currentUser = username; initChat(); showApp(); }
        else alert('Неверный логин или пароль!');
    }

    async function register() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        const res = await fetch('/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
        if (res.ok) alert('Регистрация успешна! Теперь войдите.');
        else alert('Такой пользователь уже существует!');
    }

    function initChat() {
        if (ws) ws.close();
        ws = new WebSocket('ws://' + window.location.host + '/ws');
        ws.onopen = () => { ws.send(JSON.stringify({ type: 'join', room: currentRoom, username: currentUser })); };
        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'history') {
                document.getElementById('messages').innerHTML = '';
                data.messages.forEach(m => addMessage(m));
            } else if (data.type === 'message') {
                addMessage(data);
            }
        };
        document.getElementById('currentUser').textContent = currentUser;
        loadHistory();
    }

    function addMessage(m) {
        const div = document.createElement('div');
        div.className = 'msg';
        let fileHtml = '';
        if (m.file) {
            fileHtml = m.file.match(/\\.(jpg|jpeg|png|gif|webp)$/i) ? `<img src="/uploads/${m.file}">` : `<a href="/uploads/${m.file}" target="_blank">📎 ${m.file}</a>`;
        }
        div.innerHTML = `<span class="user">${m.username}</span><span class="time">${m.time || ''}</span><div class="text">${m.text || ''} ${fileHtml}</div>`;
        document.getElementById('messages').appendChild(div);
        document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
    }

    async function loadHistory() {
        const res = await fetch(`/history/${currentRoom}`);
        const data = await res.json();
        document.getElementById('messages').innerHTML = '';
        data.forEach(m => addMessage(m));
    }

    function sendMsg() {
        const input = document.getElementById('msgInput');
        if (!input.value.trim()) return;
        ws.send(JSON.stringify({ type: 'message', room: currentRoom, username: currentUser, text: input.value }));
        input.value = '';
    }

    function sendSticker(sticker) {
        ws.send(JSON.stringify({ type: 'message', room: currentRoom, username: currentUser, text: sticker }));
    }

    async function sendFile(input) {
        const file = input.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('room', currentRoom);
        formData.append('username', currentUser);
        const res = await fetch('/upload', { method: 'POST', body: formData });
        if (res.ok) { input.value = ''; loadHistory(); }
    }

    function startCall() {
        alert('WebRTC видеозвонок в разработке — но это уже почти готово, блять!');
    }

    document.querySelectorAll('.room-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.room-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentRoom = btn.dataset.room;
            loadHistory();
            ws.send(JSON.stringify({ type: 'join', room: currentRoom, username: currentUser }));
        });
    });

    document.getElementById('msgInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMsg(); });
</script>
</body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(html)

# --- API для регистрации и логина ---
@app.post("/register")
async def register_user(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(400, "User exists")
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user = User(username=username, password=hashed)
    db.add(user)
    db.commit()
    return {"ok": True}

@app.post("/login")
async def login_user(username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
        raise HTTPException(401, "Invalid credentials")
    return {"ok": True}

# --- Загрузка файлов ---
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), room: str = Form(...), username: str = Form(...)):
    ext = file.filename.split(".")[-1]
    filename = f"{datetime.now().timestamp()}.{ext}"
    path = f"uploads/{filename}"
    async with aiofiles.open(path, "wb") as f:
        content = await file.read()
        await f.write(content)
    db = SessionLocal()
    msg = Message(room=room, username=username, text="", file=filename)
    db.add(msg)
    db.commit()
    return {"ok": True}

# --- История сообщений ---
@app.get("/history/{room}")
async def get_history(room: str):
    db = SessionLocal()
    msgs = db.query(Message).filter(Message.room == room).order_by(Message.timestamp).limit(100).all()
    return [{"username": m.username, "text": m.text, "file": m.file, "time": m.timestamp.strftime("%H:%M")} for m in msgs]

# --- WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    room = "general"
    username = "Аноним"
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "join":
                room = msg.get("room", "general")
                username = msg.get("username", "Аноним")
                if room not in active_connections:
                    active_connections[room] = []
                active_connections[room].append(websocket)
            elif msg.get("type") == "message":
                db = SessionLocal()
                new_msg = Message(room=room, username=username, text=msg.get("text", ""))
                db.add(new_msg)
                db.commit()
                for conn in active_connections.get(room, []):
                    if conn != websocket:
                        await conn.send_text(json.dumps({
                            "type": "message",
                            "username": username,
                            "text": msg.get("text", ""),
                            "time": datetime.now().strftime("%H:%M")
                        }))
    except WebSocketDisconnect:
        if room in active_connections:
            active_connections[room].remove(websocket)
