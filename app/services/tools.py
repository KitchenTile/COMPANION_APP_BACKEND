import requests



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
    print(f'AI asks: {query}')
    user_input = input("answer: ")
    return user_input


tool_dict = {
    "get_horoscope": get_horoscope,
    "get_base_conversion": get_base_conversion,
    "user_interaction": user_interaction
}

#tools available for the model
tool_definitions = [
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