import json
from typing import Optional
import uuid
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from requests import request
from services.orchestrator.memory import ConversationManager
from services.tools import tool_definitions, tool_dict
from services.prompts.prompts import prompt_dict
import os

load_dotenv()

app = FastAPI()

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


@app.get('/')
def root():
    return {"message": "FastAPI is running!"}

#get message history
@app.get('/chat/{user_id}/{chat_id}')
async def get_messages_data(chat_id: str, user_id: str):
    try:
        #inititate a new memory instance
        memory = ConversationManager(chat_id, user_id)
        return memory.messages
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=str(e))        
    
# save a message 
@app.post("/chat/message")
async def send_message(userQuery: ChatMessageRequest):
    try:
        #initiate Memory for THIS specific user
        memory = ConversationManager(userQuery.chat_id, userQuery.user_id)

        if not userQuery.task_id:
            current_task_id = str(uuid.uuid4())
        else:
            current_task_id = userQuery.task_id
        
        # init client
        client = OpenAI()

        print(current_task_id)

        #if the user message is a response to the gpt tool
        if userQuery.pending_tool_id:
            # We dont add a user message. We add a TOOL result
            memory.add_process_log(
                task_id=current_task_id,
                step_type="tool_result",
                payload={
                    "tool_call_id": userQuery.pending_tool_id, 
                    "content": userQuery.message
                }
            )
            #add the message to the front facing conversation
            memory.add_message(userQuery.message, "user")
        # if it's a normal message
        else:
            #add the message (new chat or new messaged handled in conv manager class)
            memory.add_message(userQuery.message, "user")

            #add user message to process log for the model
            memory.add_process_log(current_task_id, "user", userQuery.message)
            
        #orchestrator loop to avoid countless conditional statements
        while True:
            #model call
            completion = client.chat.completions.create(
                model="gpt-5-nano",
                messages=memory.compile_process_logs(current_task_id, prompt_dict["reasoning_agent_prompt"]),
                tools=tool_definitions,
            )

            #get model to decide if they want to use tool
            completion.model_dump()

            #if we use tools, add the message to the message array 
            if completion.choices[0].message.tool_calls:

                #add the tool usage to the process log
                memory.add_process_log(
                    task_id=current_task_id,
                    step_type="assistant_tool_call", 
                    payload=completion.model_dump() 
                )

                #and loop to use tool(s)
                for tool_call in completion.choices[0].message.tool_calls:
                    print(tool_call.function.name, tool_call.function.arguments)
                    func_name = tool_call.function.name
                    func = tool_dict[func_name]
                    func_args = json.loads(tool_call.function.arguments)

                    result = func(**func_args)

                    #check if the tool is a user question
                    if isinstance(result, dict) and result.get('action') == "ask_user":
                        print("in the user question conditional")
                        #send the question to the front end
                        memory.add_message(result['question'], "assistant")
                        #stop the function
                        return {
                            "status": "needs_info", 
                            "data": result['question'], 
                            "task_id": current_task_id,
                            "pending_tool_id": tool_call.id 
                        } 

                    #log the tool use         
                    memory.add_process_log(
                        task_id=current_task_id,
                        step_type="tool_result",
                        payload={
                            # "role": "tool",
                            "tool_call_id": tool_call.id, 
                            "content": str(result)
                        }
                    )
            else:
                break

        #second model call
        completion_2 = client.chat.completions.parse(
            model="gpt-5-nano",
            messages=memory.compile_process_logs(current_task_id, prompt_dict["reasoning_agent_prompt"]),
            tools=tool_definitions,
            response_format=QueryResponse
        )

        #output
        final_response = completion_2.choices[0].message.parsed

        memory.add_message(final_response.response, "assistant")


        return {"status": "Completed", "task_id": current_task_id, "response_text": final_response.response, "data": userQuery}

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)