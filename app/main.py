import json
from typing import Optional
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from openai import OpenAI
from pydantic import BaseModel, Field
import redis
from requests import request
# from app.services.client_agent.client_agent import ClientAgent
from app.services.client_agent.client_agent import ClientAgent
from app.services.orchestrator.memory import ConversationManager
from app.utils.websocket_manager import WebsocketManager
# from app.services.tools import tool_definitions, tool_dict
# from app.services.prompts.prompts import prompt_dict
# import os

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
            await websocket_manager.send_message(chat_id=chat_id, message=data)

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



    #OLD WHILE LOOP
        # #orchestrator loop to avoid countless conditional statements
        # while True:
        #     #model call
        #     completion = client.chat.completions.create(
        #         model="gpt-5-nano",
        #         messages=memory.compile_process_logs(current_task_id, prompt_dict["reasoning_agent_prompt"]),
        #         tools=tool_definitions,
        #     )

        #     #get model to decide if they want to use tool
        #     completion.model_dump()

        #     #if we use tools, add the message to the message array 
        #     if completion.choices[0].message.tool_calls:

        #         #add the tool usage to the process log
        #         memory.add_process_log(
        #             task_id=current_task_id,
        #             step_type="assistant_tool_call", 
        #             payload=completion.model_dump() 
        #         )

        #         #and loop to use tool(s)
        #         for tool_call in completion.choices[0].message.tool_calls:
        #             print(tool_call.function.name, tool_call.function.arguments)
        #             func_name = tool_call.function.name
        #             func = tool_dict[func_name]
        #             func_args = json.loads(tool_call.function.arguments)

        #             result = func(**func_args)

        #             #check if the tool is a user question
        #             if isinstance(result, dict) and result.get('action') == "ask_user":
        #                 print("in the user question conditional")
        #                 #send the question to the front end
        #                 memory.add_message(result['question'], "assistant")
        #                 #stop the function
        #                 return {
        #                     "status": "needs_info", 
        #                     "data": result['question'], 
        #                     "task_id": current_task_id,
        #                     "pending_tool_id": tool_call.id 
        #                 } 

        #             #log the tool use         
        #             memory.add_process_log(
        #                 task_id=current_task_id,
        #                 step_type="tool_result",
        #                 payload={
        #                     # "role": "tool",
        #                     "tool_call_id": tool_call.id, 
        #                     "content": str(result)
        #                 }
        #             )
        #     else:
        #         break

        # #second model call
        # completion_2 = client.chat.completions.parse(
        #     model="gpt-5-nano",
        #     messages=memory.compile_process_logs(current_task_id, prompt_dict["reasoning_agent_prompt"]),
        #     tools=tool_definitions,
        #     response_format=QueryResponse
        # )

        # #output
        # final_response = completion_2.choices[0].message.parsed

        # memory.add_message(final_response.response, "assistant")