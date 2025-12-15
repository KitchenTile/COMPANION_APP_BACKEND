from typing import Any, Dict, Optional
from app.services.agent_base import AgentBase


class ClientAgent(AgentBase):
    def __init__(self, name: str, client: Any, user_id: str, chat_id: str, user_message: str):
        super().__init__(name, client)

        self.user_id = user_id
        self.chat_id = chat_id
        self.user_message = user_message

    
    #call LLM with parameters for differnet model (more or less thinking) and response format
    def _LLM_call(self, response_format: Optional[Dict] = None):
        
        response = self.client.chat.completions.parse(
            model="gpt-5-nano",
            messages=self.memory.compile_process_logs(self.task_id, self.prompt),
            response_format=response_format
        )

        return response

    def _cathegorise_message(self):

        #make an LLM call to figure out what to do with the user message
        return
