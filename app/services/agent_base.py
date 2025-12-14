

from abc import ABC, abstractmethod
from typing import Any, Dict


class AgentBase(ABC):
    def __init__(self, client: Any, name: str, ):
        self.client = client
        self.name = name

    @abstractmethod
    def receive_message(self, packet: Dict[str, Any]) -> Dict[str, Any]:
       pass
        