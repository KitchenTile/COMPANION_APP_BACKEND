from typing import Any, Dict, Optional
from openai import OpenAI
from pydantic import BaseModel
from app.services.agent_base import AgentBase
from app.services.prompts.prompts import prompt_dict

from dotenv import load_dotenv


load_dotenv()

class CategorizeResponse(BaseModel):
    intent: str
    

class ClientAgent(AgentBase):
    def __init__(self, name: str, client: Any, user_id: str, chat_id: str, user_message: str):
        super().__init__(name = name, client = client)

        self.user_id = user_id
        self.chat_id = chat_id
        self.user_message = user_message
        self.message_intent = self._categorize_message_intent(response_format=CategorizeResponse)

    def receive_message(self, packet):
        return super().receive_message(packet)
    
    def get_intent(self):
        return self.message_intent


    def _categorize_message_intent(self, response_format: Optional[Any] = None):
        #make an LLM call to figure out what to do with the user message
        response = self.client.responses.parse(
            model="gpt-5-nano",
            input=self.user_message,
            instructions="Categorize the user message into ONE of the following intents: SOCIAL, EMERGENCY, TASK",
            # response_format=response_format
        )

        print("user intent:")
        print(response.output[1].content[0].text)

            
        return response.output[1].content[0].text
    
        #reply to non urgent message
    def _handle_social_message(self):


        response = self.client.responses.parse(
            model="gpt-5-nano",
            input=prompt_dict["front_facing_agent_social_prompt"]
        )
    
client = OpenAI()

client_agent = ClientAgent("Client_Agent", client, "user_id", chat_id="Chat_id", user_message="THIS IS AN EMERGENCY TEXT!")
