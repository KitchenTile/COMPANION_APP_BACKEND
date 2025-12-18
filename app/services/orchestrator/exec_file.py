import json
from dotenv import load_dotenv
from openai import OpenAI
import redis

from app.services.orchestrator.orchestrator_agent import OrchestratorAgent
from app.services.tools import tool_definitions, tool_dict
from app.services.prompts.prompts import prompt_dict

load_dotenv()

client = OpenAI()

r = redis.Redis(host='localhost', port=6379, db=0)


while True:

    print("exec file running")
    #get data from queue
    _, raw_data = r.blpop('orchestrator_queue') 
    print(raw_data)
    
    #define packet to send the agent
    packet = json.loads(raw_data)
    print(f"Received task: {packet['task_id']}")
    
    #initialise the agent
    orchestrator = OrchestratorAgent(name="OrchestratorAgent",client=client ,tool_definitions=tool_definitions, tool_dict=tool_dict, prompt=prompt_dict["reasoning_agent_prompt"], user_id=packet["user_id"], chat_id=packet["chat_id"])

    print("---")
    print(orchestrator)
    print("---")
    #call function to run the loop
    result = orchestrator.receive_message(packet)

    result_dump = json.dumps(result)

    #oublish it
    r.publish(f"chat_updates_{packet['chat_id']}", result_dump)