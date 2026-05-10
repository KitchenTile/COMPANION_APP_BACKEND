# SafeStep
# Copyright (c) 2026 Azul P Debenedetti and Middlesex University.
# Exclusive commercial license held by Fountech AI Limited.
# See LICENSE.txt for terms.

import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import redis

from app.services.anticip8.anticip8_manager import Anticip8RoutePredictor
from app.services.orchestrator.orchestrator_agent import OrchestratorAgent
from app.services.tools import tool_definitions, tool_dict
from app.services.prompts.prompts import prompt_dict
from app.utils.journey_planner import JourneyPlanner

load_dotenv()

client = OpenAI()

redis_host = os.getenv("REDIS_HOST", "localhost")

r = redis.Redis(host=redis_host, port=6379, db=0)


while True:

    print("exec file running")
    #get data from queue
    _, raw_data = r.blpop('orchestrator_queue') 
    print(raw_data)
    
    #define packet to send the agent
    packet = json.loads(raw_data)
    print(f"Received task: {packet['task_id']}")

    anticip8 = Anticip8RoutePredictor()


    journey_planner = JourneyPlanner(tools = None, anticip8 = anticip8)
    
    #initialise the agent
    orchestrator = OrchestratorAgent(name="OrchestratorAgent",client=client ,tool_definitions=tool_definitions, tool_dict=tool_dict, prompt=prompt_dict["reasoning_agent_prompt"], user_id=packet["user_id"], chat_id=packet["chat_id"], journey_planner = journey_planner)

    #call function to run the loop
    result = orchestrator.receive_message(packet)

    result_dump = json.dumps(result)

    print("------- result_log ------")

    print(result)

    #oublish it
    r.publish(packet['chat_id'], result_dump)
    