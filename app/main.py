import json
from typing import Optional
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from openai import OpenAI
from pydantic import BaseModel, Field
import redis
from app.services.client_agent.client_agent import ClientAgent
from app.services.orchestrator.memory import ConversationManager
from app.utils.websocket_manager import WebsocketManager


load_dotenv()

app = FastAPI()

r = redis.Redis(host='localhost', port=6379, db=0)


# Pydantic model for incoming JSON body
class ChatMessageRequest(BaseModel):
    chat_id: str
    user_id: str
    message: str
    task_id: Optional[str] = None 
    pending_tool_id: Optional[str] = None 


#interface for the response
class QueryResponse(BaseModel):
    processes: list[str] = Field(
        description="an array of processes fulfilled to succesfully complete user's query"
    )
    response: str = Field(
        description="A natural language response to the user's question."
    )
    task_id: str = Field(
        description="current task id"
    )

websocket_manager = WebsocketManager()


@app.get('/')
def root():
    return {"message": "FastAPI is running!"}

#get message history
@app.get('/chat/{user_id}/{chat_id}')
async def get_messages_data(chat_id: str, user_id: str):
    try:
        #inititate a new memory instance
        memory = ConversationManager(chat_id, user_id)
        # and send messages
        return memory.messages
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))   

#websocket decorator keeps while loop running
@app.websocket('/ws/{chat_id}')
async def websocket_endpoint(websocket: WebSocket, chat_id: str):
    #connect manager
    await websocket_manager.connect(chat_id=chat_id, websocket=websocket)
    try:
        while True:
            data = await websocket.receive_text()

            print(data)
            try:
                packet = json.loads(data)
                if packet.get("receiver") == "ORCHESTRATOR_AGENT":
                    print(f"sending task to {packet.receiver}")

                    #dispatch task to orchestrator agent
                    r.lpush("orchestrator_queue", data)
                else:
                    await websocket_manager.send_message(chat_id=chat_id, message=data)


            except Exception as e:
                print(f"Error handling data: {e}")

    except WebSocketDisconnect:
        await websocket_manager.disconnect(chat_id=chat_id, websocket=websocket)
    

# save a message 
@app.post("/chat/message")
async def send_message(userQuery: ChatMessageRequest):
    try:
        
        if not userQuery.task_id:
            current_task_id = str(uuid.uuid4())
        else:
            current_task_id = userQuery.task_id
        
        # init client
        client = OpenAI()

        print('task id')
        print(current_task_id)
        print('pending tool id')
        print(userQuery.pending_tool_id)
        
        client_agent = ClientAgent(name="Client_Agent", client=client, user_id=userQuery.user_id, chat_id=userQuery.chat_id, dispatcher=r, user_message=userQuery.message, pending_tool_id=userQuery.pending_tool_id, task_id=current_task_id)

        response = client_agent.handle_message()

        print("response")
        print(response)


        return {"status": response['status'], "task_id": current_task_id, "response_text": response['answer'], "data": userQuery}

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
