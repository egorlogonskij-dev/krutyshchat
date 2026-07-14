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
    <h1>🔥 КРУТЫШ ЧАТ 🔥</h1>
    <div id="messages"></div>
    <input type="text" id="msgInput" placeholder="Пиши сюда, блять...">
    <button onclick="sendMsg()">ОТПРАВИТЬ</button>
    <script>
        const ws = new WebSocket("ws://" + window.location.host + "/ws/" + prompt("Твой ID:"));
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            document.getElementById("messages").innerHTML += 
                "<div class='msg'><span class='time'>[" + msg.timestamp + "]</span> <strong>" + msg.from + ":</strong> " + msg.text + "</div>";
        };
        function sendMsg() {
            const input = document.getElementById("msgInput");
            ws.send(JSON.stringify({ text: input.value }));
            input.value = "";
        }
    </script>
</body>
</html>
"""

active_connections = []

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    active_connections.append({"id": client_id, "socket": websocket})
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg["timestamp"] = datetime.now().isoformat()
            msg["from"] = client_id
            for conn in active_connections:
                if conn["id"] != client_id:
                    await conn["socket"].send_text(json.dumps(msg))
    except WebSocketDisconnect:
        active_connections.remove({"id": client_id, "socket": websocket})
