# server.py — полная версия с кнопкой и полем ввода (для Render)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
from datetime import datetime

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
<head>
    <title>KRUTYSH CHAT</title>
    <style>
        body { background: #0a0a0a; color: #00ff88; font-family: monospace; }
        #messages { height: 400px; overflow-y: scroll; border: 1px solid #00ff88; padding: 10px; }
        .msg { margin: 5px 0; }
        .time { color: #666; font-size: 12px; }
        input { background: #1a1a1a; color: #00ff88; border: 1px solid #00ff88; padding: 10px; width: 70%; }
        button { background: #00ff88; color: #0a0a0a; padding: 10px 20px; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🔥 KRUTYSH CHAT 🔥</h1>
    <div id="messages"></div>
    <input type="text" id="msgInput" placeholder="Пиши сюда, блять...">
    <button onclick="sendMsg()">ОТПРАВИТЬ</button>

    <script>
        let username = prompt("Твой ник:") || "Аноним";
        // Автоматически определяем wss:// если страница открыта по HTTPS
        const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const ws = new WebSocket(protocol + "//" + window.location.host + "/ws");

        ws.onopen = () => {
            ws.send(JSON.stringify({ type: "join", username: username }));
        };

        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            if (msg.type === "history") {
                document.getElementById("messages").innerHTML = "";
                msg.messages.forEach(m => addMessage(m));
            } else if (msg.type === "message") {
                addMessage(msg);
            }
        };

        function addMessage(m) {
            const div = document.createElement("div");
            div.className = "msg";
            div.innerHTML = `<span class="time">[${m.time || ""}]</span> <strong>${m.username}:</strong> ${m.text}`;
            document.getElementById("messages").appendChild(div);
            document.getElementById("messages").scrollTop = document.getElementById("messages").scrollHeight;
        }

        function sendMsg() {
            const input = document.getElementById("msgInput");
            if (!input.value.trim()) return;
            ws.send(JSON.stringify({ type: "message", text: input.value }));
            input.value = "";
        }

        document.getElementById("msgInput").addEventListener("keydown", (e) => {
            if (e.key === "Enter") sendMsg();
        });
    </script>
</body>
</html>
"""

active_connections = []

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = "Аноним"
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "join":
                username = msg.get("username", "Аноним")
                active_connections.append(websocket)
                # Отправить историю (5 последних сообщений)
                # Здесь можно добавить реальную историю
            elif msg.get("type") == "message":
                for conn in active_connections:
                    if conn != websocket:
                        await conn.send_text(json.dumps({
                            "type": "message",
                            "username": username,
                            "text": msg.get("text", ""),
                            "time": datetime.now().strftime("%H:%M")
                        }))
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
