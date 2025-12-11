
import uuid
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import requests
import json
from services.melelem.memory import ConversationManager
from services.tools import tool_definitions, tool_dict
from services.prompts.prompts import prompt_dict

#load env file
load_dotenv()

conversation_memory = ConversationManager("5616b7de-165c-44a9-88a7-e2b5d2e4523d", "5616b7de-165c-44a9-88a7-e2b5d2e4523c")

conversation_memory.messages
# init client
client = OpenAI()

current_task_id = str(uuid.uuid4())

conversation_memory.add_process_log(current_task_id, "user", 'what is my horoscope for today?')

    
#orchestrator loop to avoid countless conditional statements
while True:
    #model call
    completion = client.chat.completions.create(
        model="gpt-5-nano",
        messages=conversation_memory.compile_process_logs(current_task_id, prompt_dict["reasoning_agent_prompt"]),
        tools=tool_definitions,
    )

    #get model to decide if they want to use tool
    completion.model_dump()

    #if we use tools, add the message to the message array 
    if completion.choices[0].message.tool_calls:

        #add the tool usage to the process log
        conversation_memory.add_process_log(
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

            if result["action"] == "ask_user":
                conversation_memory.add_process_log(
                    task_id=current_task_id,
                    step_type="tool_result",
                    payload={
                        # "role": "tool",
                        "tool_call_id": tool_call.id, 
                        "content": str(result)
                    }
                )
                print("User needs to ask question")
                break

            conversation_memory.add_process_log(
                task_id=current_task_id,
                step_type="tool_result",
                payload={
                    # "role": "tool",
                    "tool_call_id": tool_call.id, 
                    "content": str(result)
                }
            )
    else:
        print(completion.choices[0].message)
        break

#interface for the response
class QueryResponse(BaseModel):
    processes: list[str] = Field(
        description="an array of processes fulfilled to succesfully complete user's query"
    )
    response: str = Field(
        description="A natural language response to the user's question."
    )

#second model call
completion_2 = client.chat.completions.parse(
    model="gpt-5-nano",
    messages=conversation_memory.compile_process_logs(current_task_id, prompt_dict["reasoning_agent_prompt"]),
    tools=tool_definitions,
    response_format=QueryResponse
)

#output
final_response = completion_2.choices[0].message.parsed

print(final_response)
