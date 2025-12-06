from pydantic import BaseModel, Field

class QueryResponse(BaseModel):
    processes: list[str] = Field(
        description="List of steps taken to complete the request"
    )
    response: str = Field(
        description="The final natural language answer"
    )