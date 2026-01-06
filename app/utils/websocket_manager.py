import os
from typing import Any, Dict
import asyncio
import redis.asyncio as aioredis
import json
from fastapi import WebSocket

class RedisPubSubManager:
    def __init__(self, host: str = os.getenv("REDIS_HOST", "localhost"), port: int = 6379):
        self.host = host
        self.port = port
        self.pubsub = None
        self.redis_connection = None

    async def _get_redis_connection(self) -> aioredis.Redis:
        return aioredis.Redis(host=self.host, port=self.port,auto_close_connection_pool=False)
    
    #connect and initiate redis pubsub
    async def connect(self) -> None:
        self.redis_connection = await self._get_redis_connection()
        self.pubsub = self.redis_connection.pubsub()

    async def _publish(self, channel: str, message: str):
        return self.redis_connection.publish(channel, message)
    
    async def subscribe(self, channel: str) -> aioredis.Redis:
        await self.pubsub.subscribe(channel)
        return self.pubsub

    async def unsubscribe(self, channel: str) -> None:
        await self.pubsub.unsubscribe(channel)




class WebsocketManager:
    def __init__(self):
        self.active_connections: Dict = {}
        self.pubsub_client = RedisPubSubManager()
        self.tasks = {}


    async def connect(self, chat_id:str, websocket: WebSocket) -> None:
        await websocket.accept()

        #add to active connections registry
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []

            await self.pubsub_client.connect()
            pubsub_subscriber = await self.pubsub_client.subscribe(chat_id)
            task = asyncio.create_task(self._pubsub_data_reader(pubsub_subscriber))
            self.tasks[chat_id] = task
            
        self.active_connections[chat_id].append(websocket)


    async def disconnect(self, chat_id:str, websocket):
        #disconnect the socket if it exists
        if chat_id in self.active_connections:
            if websocket in self.active_connections[chat_id]:
                self.active_connections[chat_id].remove(websocket)

            if len(self.active_connections[chat_id]) == 0:
                del self.active_connections[chat_id]
                await self.pubsub_client.unsubscribe(channel=chat_id)

                if chat_id in self.tasks:
                    self.tasks[chat_id].cancel()
                    del self.tasks[chat_id]

    async def send_message(self, chat_id, message):
        # find the socket for the chat id
        if chat_id in self.active_connections:
            for socket in self.active_connections[chat_id]:
                #send the message
                await socket.send_text(message)

    async def _pubsub_data_reader(self, pubsub_subscriber):
            try:
                while True:
                    message = await pubsub_subscriber.get_message(ignore_subscribe_messages=True)
                    if message is not None:
                        chat_id = message['channel'].decode('utf-8')
                        if chat_id in self.active_connections:
                            data = message['data'].decode('utf-8')
                            for socket in self.active_connections[chat_id]:
                                await socket.send_text(data)
                    # Small sleep to prevent CPU spiking
                    await asyncio.sleep(0.01) 
            except asyncio.CancelledError:
                # Handle clean exit when we cancel the task
                pass

    