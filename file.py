from openai import OpenAI
from pydantic import BaseModel, Field
import requests
import json


client = OpenAI()

#tools available for the model
tools = [
    {
        "type": "function",
        "function":{
        "name": "get_horoscope",
        "description": "Get horoscope for an astrological and specific time.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "sign": {
                    "type": "string",
                    "description": "An astrological sign like Taurus or Aquarius",
                },
                "day": {
                    "type": "string",
                    "description": "When do we want the horoscope information from",
                },
            },
            "required": ["sign", "day"],
            "additionalProperties": False
        },
        }
    },
    {
        "type": "function",
        "function":{
        "name": "get_base_conversion",
        "description": "Given a number, a starting base (optional) and a target base, convert that number into the desired base.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": "The number to be converted",
                },
                "target_base": {
                    "type": "integer",
                    "description": "The desired base to convert the number to",
                },
                "starting_base": {              
                    "type": ["integer", "null"],
                    "description": "The base the number is originally in",
                },
            },
            "required": ["number", "target_base", "starting_base"],
            "additionalProperties": False
        },
        }
    },
    {
        "type": "function",
        "function":{
        "name": "user_interaction",
        "description": "In the case of missing piece of information or confirmation needed to complete a task, use tool to interact with user.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Information request string",
                },
            },
            "required": ["query"],
            "additionalProperties": False
        },
        }
    },
]

#tool def
def get_horoscope(sign: str, day: str):
    headers = {
        'accept': 'application/json'
    }
    try:
        if day == "today" or day == "tomorrow" or day == "yesterday":
            response = requests.get(f"https://horoscope-app-api.vercel.app/api/v1/get-horoscope/daily?sign={sign}&day={day}", headers=headers)
        else:
            response = requests.get(f"https://horoscope-app-api.vercel.app/api/v1/get-horoscope/{day}?sign={sign}", headers=headers)


        response.raise_for_status() 
        data = response.json()
        return data['data']

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

#tool def
def get_base_conversion(number:int, target_base: int, starting_base: int|None=10):
    headers = {
        'accept': 'application/json'
    }
    try:
        response = requests.get(f"https://api.math.tools/numbers/base?number={number}&from={starting_base}&to={target_base}", headers=headers)

        response.raise_for_status()
        data = response.json()
        
        return data['contents'];

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

#tool def
def user_interaction(query: str):
    return query


tool_dict = {
    "get_horoscope": get_horoscope,
    "get_base_conversion": get_base_conversion
}

#array of messages to give the model context
messages=[
    {"role": "system", "content": "You're an asistant in charge of interpreting and fulfilling a request"},
    {"role": "user", "content": "I'm a Cancer, please summarize my horoscope for 'today' and also my 'weekly'. Can you also convert the number 10 from base 10 to base 2"},
]
    
#orchestrator loop to avoid countless conditional statements
while True:
    #model call
    completion = client.chat.completions.create(
        model="gpt-5-nano",
        messages=messages,
        tools=tools,
    )

    #get model to decide if they want to use tool
    completion.model_dump()

    #if we use tools, add the message to the message array 
    if completion.choices[0].message.tool_calls:
        messages.append(completion.choices[0].message)

        #and loop to use tool(s)
        for tool_call in completion.choices[0].message.tool_calls:
            print(tool_call.function.name, tool_call.function.arguments)
            func_name = tool_call.function.name
            func = tool_dict[func_name]
            func_args = json.loads(tool_call.function.arguments)

            result = func(**func_args)
            messages.append(
                {"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result)}
            )
    else:
        print("Unstructured response")
        print(completion.choices[0].message.content)
        break

#interface for the response
class QueryResponse(BaseModel):
    processes: list[str] = Field(
        description="an array of processes fulfilled to succesfully complete user's query"
    )
    response: str = Field(
        description="A natural language response to the user's question."
    )

#second model call
completion_2 = client.chat.completions.parse(
    model="gpt-5-nano",
    messages=messages,
    tools=tools,
    response_format=QueryResponse
)

#output
final_response = completion_2.choices[0].message.parsed
