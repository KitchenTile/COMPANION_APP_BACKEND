import json
from typing import Any, Dict, Optional
from uuid import uuid4
from openai import OpenAI
from pydantic import BaseModel
from app.services.agent_base import AgentBase
from app.services.orchestrator.memory import ConversationManager
from app.services.prompts.prompts import prompt_dict

from dotenv import load_dotenv



load_dotenv()

class CategorizeResponse(BaseModel):
    intent: str
    

class ClientAgent(AgentBase):
    def __init__(self, name: str, client: Any, user_id: str, chat_id: str, dispatcher: Any, user_message: str, pending_tool_id: Any, task_id: str):
        super().__init__(name = name, client = client)

        self.user_id = user_id
        self.chat_id = chat_id
        self.task_id = task_id
        self.user_message = user_message
        self.pending_tool_id = pending_tool_id
        self.message_intent = self._categorize_message_intent()
        self.memory = ConversationManager(chat_id, user_id)
        self.dispatcher = dispatcher


    def receive_message(self, packet):
        return super().receive_message(packet)
    
    def get_intent(self):
        return self.message_intent
    
    def handle_message(self):
        if self.message_intent == "SOCIAL":
            #handle social message
            return self._handle_social_message()

        elif self.message_intent == "TASK" or self.message_intent == "TOOL_USE":
            #handle task usage
            self._handle_task_message()

        elif self.message_intent == "EMERGENCY":
            #handle emergency
            return


    def _categorize_message_intent(self):
        try:
            if self.pending_tool_id != None:
                return "TOOL_USE"

            #make an LLM call to figure out what to do with the user message
            response = self.client.responses.parse(
                model="gpt-5-nano",
                input=self.user_message,
                instructions="Categorize the user message into ONE of the following intents: SOCIAL, EMERGENCY, TASK (TASK includes asking for horoscope)",
            )

            print("user intent:")
            print(response.output[1].content[0].text)

                
            return response.output[1].content[0].text
        
        except Exception as e:
            print(f"Server Error In categorize message: {e}")
    
    #reply to non urgent message
    def _handle_social_message(self):

        #add user message to DB
        self.memory.add_message(self.user_message, "user")

        #GPT call
        response = self.client.responses.parse(
            model="gpt-5-nano",
            instructions=prompt_dict["front_facing_agent_social_prompt"],
            input=self.user_message
        )

        final_response = response.output[1].content[0].text

        #add response to DB
        self.memory.add_message(final_response, "assistant")

        return response.output[1].content[0].text
    
    #send task to redis queue for other agent
    def _handle_task_message(self):
        try:

            #add user message to DB
            self.memory.add_message(self.user_message, "user")

            #create packet
            packet = {
                "message_id": str(uuid4()),
                "chat_id": self.chat_id,
                "sender": self.name,
                "resiver": "orchestrator_agent",
                "performative": "REQUEST",

                "user_id": self.user_id,
                "task_id": self.task_id,
                "pending_tool_id": self.pending_tool_id,

                "content": {"message": self.user_message},
            }
            print(packet)

            packet_json = json.dumps(packet)


            #dispatch
            self.dispatcher.lpush("orchestrator_queue", packet_json)
            print("past sending")


            #if there's no tool usage
            if self.pending_tool_id != None:
                #add quick response to db
                self.memory.add_message('Absolutely, let me get that ready and come back with the answer in just a minute.', 'assistant')
                return "Absolutely, let me get that ready and come back with the answer in just a minute."

        except Exception as e:
            print(f"Server Error In handle task: {e}")
    

    
client = OpenAI()

# client_agent = ClientAgent("Client_Agent", client, "user_id", chat_id="Chat_id", user_message="Hi! How are you?")

# client_agent.handle_message()
