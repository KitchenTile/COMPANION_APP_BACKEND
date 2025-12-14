from app.services.agent_base import AgentBase


class ClientAgent(AgentBase):
    def __init__(self, name: str):
        self.name = name