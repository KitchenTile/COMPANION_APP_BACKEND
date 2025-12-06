from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# import supabase
import datetime
import uvicorn


app = FastAPI()

class ChatMessage(BaseModel):
    chat_id: str;
    message: str;


@app.get('/')
def root():
    return {"message": "FastAPI!"}

# # Controller equivalent
# @app.get("/chats")
# async def get_all_chats():
#     try:
#         response = supabase.table("chats").select("*").execute()
#         if response.error:
#             raise HTTPException(status_code=400, detail=response.error.message)
#         return response.data
#     except Exception as e:
#         print(e)
#         raise HTTPException(status_code=500, detail="Internal server error")
    
@app.post("/chats/")
async def create_chat(userQuery: ChatMessage):
    try:
        # response = supabase.table("chats").select("*")
        x = datetime.datetime.now()
        print(x)
        print(userQuery)
        return userQuery

        
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal server error")
    
def start_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    uvicorn.run("main:app", host=host, port=port, reload=reload)
    

if __name__ == "__main__":
    start_server()