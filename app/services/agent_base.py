

from abc import ABC


class AgentBase(ABC):
    def __init__(self, client):
        self.client = client

    
    def recieve_message(self):
        pass
        