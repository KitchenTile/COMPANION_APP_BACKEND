from typing import Any, Dict, Optional
from pydantic import BaseModel

#standarised communication base model
class AgentMessage(BaseModel):
    #FIPA header
    nessage_id: str
    conversation_id: str
    sender: str
    resiver: str
    performative: str

    user_id: str
    task_id: Optional[str] = None

    #actual message sent
    content: Dict[str, Any]