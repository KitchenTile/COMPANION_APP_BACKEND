from typing import Any


class WebsocketManager:
    def __init__(self):
        self.active_connections = {}


    async def connect(self, chat_id:str, websocket:Any):
        await websocket.accept()
        #add websocket to connection object
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        
        self.active_connections[chat_id].append(websocket)


    def disconnect(self, chat_id:str, websocket):
        #disconnect the socket
        self.active_connections[chat_id].remove(websocket)

    async def send_message(self, chat_id, message):
        # find the socket for the chat id
        if chat_id in self.active_connections:
            for conn in self.active_connections[chat_id]:
                #send the message
                await conn.send_text(message)

    