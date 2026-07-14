from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
from datetime import datetime

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<head>
    <title>KRUTYSH CHAT 2.0 🔥</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #0a0a0a; color: #00ff88; font-family: 'Courier New', monospace; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .chat-container { width: 90%; max-width: 800px; background: #111; border: 2px solid #00ff88; border-radius: 20px; padding: 20px; box-shadow: 0 0 30px #00ff8855; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #00ff8855; padding-bottom: 10px; }
        .header h1 { font-size: 24px; text-shadow: 0 0 10px #00ff88; }
        .online { color: #88ffaa; font-size: 14px; }
        #messages { height: 400px; overflow-y: auto; padding: 10px; background: #0d0d0d; border-radius: 10px; margin: 15px 0; border: 1px solid #00ff8844; }
        .msg { margin: 8px 0; padding: 6px 10px; border-radius: 8px; background: #1a1a1a; border-left: 3px solid #00ff88; }
        .msg .user { color: #88ffaa; font-weight: bold; }
        .msg .time { color: #666; font-size: 11px; margin-left: 10px; }
        .msg .text { color: #ddd; margin-top: 4px; }
        .input-area { display: flex; gap: 10px; margin-top: 10px; }
        #msgInput { flex: 1; background: #1a1a1a; color: #00ff88; border: 1px solid #00ff8855; padding: 12px; border-radius: 30px; outline: none; font-size: 16px; }
        #msgInput:focus { border-color: #00ff88; box-shadow: 0 0 15px #00ff8844; }
        button { background: #00ff88; color: #0a0a0a; border: none; padding: 12px 24px; border-radius: 30px; font-weight: bold; cursor: pointer; transition: 0.2s; font-size: 16px; }
        button:hover { background: #88ffaa; box-shadow: 0 0 20px #00ff88aa; }
        .room-selector { display: flex; gap: 10px; margin-bottom: 10px; }
        .room-btn { background: #222; color: #00ff88; border: 1px solid #00ff8844; padding: 6px 16px; border-radius: 20px; cursor: pointer; }
        .room-btn.active { background: #00ff8833; border-color: #00ff88; }
        .private-hint { color: #88aaff; font-size: 12px; margin-top: 5px; }
        .emoji-btn { background: none; border: none; font-size: 20px; cursor: pointer; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #0a0a0a; }
        ::-webkit-scrollbar-thumb { background: #00ff88; border-radius: 10px; }
    </style>
</head>
<body>
<div class="chat-container">
    <div class="header">
        <h1>💬 KRUTYSH CHAT 2.0</h1>
        <span class="online">👥 <span id="onlineCount">0</span> онлайн</span>
    </div>
    <div class="room-selector">
        <button class="room-btn active" data-room="general">#общий</button>
        <button class="room-btn" data-room="random">#флуд</button>
        <button class="room-btn" data-room="private">#секрет</button>
    </div>
    <div id="messages"></div>
    <div class="private-hint">💬 Напиши @ник чтобы отправить личное сообщение</div>
    <div class="input-area">
        <input type="text" id="msgInput" placeholder="Введите сообщение...">
        <button onclick="sendMsg()">📤</button>
    </div>
</div>
<script>
    let currentRoom = 'general';
    let username = prompt('Введи свой ник:') || 'Аноним';
    const ws = new WebSocket('ws://' + window.location.host + '/ws');
    const msgInput = document.getElementById('msgInput');
    const messages = document.getElementById('messages');
    const onlineSpan = document.getElementById('onlineCount');

    ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'join', room: currentRoom, username }));
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'online') {
            onlineSpan.textContent = data.count;
            return;
        }
        if (data.type === 'message') {
            const div = document.createElement('div');
            div.className = 'msg';
            div.innerHTML = `
                <span class="user">${data.username}</span>
                <span class="time">${data.time}</span>
                <div class="text">${data.text}</div>
            `;
            messages.appendChild(div);
            messages.scrollTop = messages.scrollHeight;
        }
    };

    function sendMsg() {
        const text = msgInput.value.trim();
        if (!text) return;
        ws.send(JSON.stringify({ type: 'message', room: currentRoom, username, text }));
        msgInput.value = '';
    }

    msgInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') sendMsg(); });

    document.querySelectorAll('.room-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.room-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentRoom = btn.dataset.room;
            messages.innerHTML = '';
            ws.send(JSON.stringify({ type: 'join', room: currentRoom, username }));
        });
    });
</script>
</body>
</html>
"""

active_connections = {}
online_count = 0

@app.get("/")
async def root():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global online_count
    await websocket.accept()
    online_count += 1
    room = 'general'
    username = 'Аноним'
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get('type') == 'join':
                room = msg.get('room', 'general')
                username = msg.get('username', 'Аноним')
                active_connections.setdefault(room, []).append(websocket)
                await websocket.send_text(json.dumps({'type': 'online', 'count': online_count}))
            elif msg.get('type') == 'message':
                for conn in active_connections.get(msg.get('room'), []):
                    if conn != websocket:
                        await conn.send_text(json.dumps({
                            'type': 'message',
                            'username': msg.get('username'),
                            'text': msg.get('text'),
                            'time': datetime.now().strftime('%H:%M')
                        }))
    except WebSocketDisconnect:
        online_count -= 1
        if room in active_connections:
            active_connections[room].remove(websocket)
