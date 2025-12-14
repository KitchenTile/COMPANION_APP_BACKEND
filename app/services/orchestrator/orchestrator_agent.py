from typing import Any, Dict, Optional
from app.services.agent_base import AgentBase


class OrchestratorAgent(AgentBase):
    def __init__(self, name: str, tools: list[Dict, Any], prompt: str):
        self.name = name
        self.tools = tools
        self.prompt = prompt

    def final_response_call(self, tools, model, messages, response_format):
        final_response = self.client.chat.completions.parse(
            model=model,
            messages=messages,
            tools=tools,
            response_format=response_format
        )