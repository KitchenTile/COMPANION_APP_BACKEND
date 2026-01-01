import json
import os
import secrets
from typing import Optional
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from authlib.integrations.starlette_client import OAuth, OAuthError
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from openai import OpenAI
from pydantic import BaseModel, Field
import redis
from app.services.client_agent.client_agent import ClientAgent
from app.services.orchestrator.memory import ConversationManager
from app.services.user_manager import CredentialManager
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

class userLogin(BaseModel):
    email: str
    password: str

class userSignUp(BaseModel):
    email: str
    password: str
    name: str

app.add_middleware(SessionMiddleware, secret_key="secretsecret")


# OAuth Setup
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("OAUTH_CLIENT2_ID"),
    client_secret=os.getenv("OAUTH_CLIENT2_SECRET"),
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    access_token_url="https://oauth2.googleapis.com/token",
    refresh_token_url="https://oauth2.googleapis.com/token",
    jwks_uri="https://www.googleapis.com/oauth2/v3/certs",
    client_kwargs={
        "scope": "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.modify",
    },
    authorize_params={
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "false",
    },
)

# JWT Configurations
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

@app.get('/gmailLogin')
async def gmail_login(request: Request, user_id: str):

    # save user_id to the session cookie
    request.session['user_id'] = user_id

    print('user_id from session')
    print(request.session['user_id'])

    #redirect url for OAuth
    url = request.url_for('gmail_auth')

    #when gmail login endpoint is hit redirect to callback endpoint
    return await oauth.google.authorize_redirect(request, url)

@app.get('/oauth/google/callback')
async def gmail_auth(request: Request):

    user_id = request.session.get("user_id")

    print("user Id callback")
    print(user_id)

    #iniitiate user manager instance with user id
    credential_manager = CredentialManager()

    try:
        #authlib performs post request and exchanges the access token for our token dict
        #including access token and refresh token
        token = await oauth.google.authorize_access_token(request)
        print("token")
        print(token)
        print(token.get("access_token"))

        if token:
            print(" -- adding token to database -- ")
            #add tokens to db
            credential_manager.add_google_tokens(user_id, token.get("access_token"), token.get('refresh_token'))



    except OAuthError as e:
        print(f"error: {e}")

    session = secrets.token_urlsafe(32)

    print(session)

    #return to the app when auth happens
    redirect_url = f"aicompanion://auth?status=success&user_id={user_id}"

    return RedirectResponse(redirect_url)

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
                    print(f"sending task to {packet.get("receiver")}")

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
