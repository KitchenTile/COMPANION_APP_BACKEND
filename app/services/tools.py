import requests
import dotenv
import os

dotenv.load_dotenv()


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
    return {"action": "ask_user", "question": query}


#tool def
def calculate_google_maps_route(origin: str, destination: str, transport_mode: list[str]):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_API_KEY"),
        "X-Goog-FieldMask": "routes.*"
    }

    try:
        data = {
            "origin": {
                "address": origin
                },
            "destination": {
                "address": destination
                },
            "travelMode": "TRANSIT",
            "computeAlternativeRoutes": False,
            "transitPreferences": {
                "routingPreference": "LESS_WALKING",
                "allowedTravelModes": transport_mode
            }
        }

        response = requests.post('https://routes.googleapis.com/directions/v2:computeRoutes', headers=headers, json=data)    

        data = response.json()

        if not data['routes'][0]:
             return "No routes found"
        
        route = data['routes'][0]

        #get encoded polyline for the location tracking
        encodedPolyline = route.get('legs', {}).get('polyline').get('encodedPolyline')

        #get fastest route metadata
        route_summary = {
            "duration": route.get("localizedValues", {}).get("duration", {}).get("text"),
            "distance": route.get("localizedValues", {}).get("distance", {}).get("text"),
            "fare": route.get("localizedValues", {}).get("transitFare", {}).get("text", "N/A"),
            "steps": []
        }

        # go through the route steps and add them to the summary
        for leg in route.get("legs", []):
            for index, step in enumerate(leg.get("steps", [])):

                # Handle Transit Details
                if "transitDetails" in step:
                    transit = step["transitDetails"]
                    line = transit.get("transitLine", {})

                    step_instruction = (
                        f"Step {index + 1}: "
                        f"Take {line.get('vehicle', {}).get('name', {}).get('text')} "
                        f"{line.get('nameShort', line.get('name'))} "
                        f"towards {transit.get('headsign')} "
                        f"for {transit.get('stopCount')} stops ({step.get("localizedValues", {}).get("staticDuration", {}).get("text")}), "
                        f"from {transit.get("stopDetails", {}).get("departureStop", {}).get("name")} "
                        f"until {transit.get("stopDetails", {}).get("arrivalStop", {}).get("name")}."
                    )
                    

                # Handle Walking Details
                elif "navigationInstruction" in step:
                    nav = step["navigationInstruction"]

                    step_instruction = (
                        f"Step {index + 1}: {nav.get("instructions", "Walk")}. "
                        f"It should take {step.get("localizedValues", {}).get("staticDuration", {}).get("text")} ({step.get("localizedValues", {}).get("distance", {}).get("text")})"
                    )
                
                route_summary["steps"].append(step_instruction)
        
        steps_string = "\n".join(route_summary['steps'])
                
        final_string = (
            f"The trip should take a total of {route_summary['duration']} and cost around {route_summary['fare']}.\n\n"
            f"Here are the steps:\n{steps_string}"
        )
        
        # return the polyline for user tracking and the text for the agent's response 
        return {
            "text": final_string,
            "polyline": encodedPolyline,
            "action": "display_route"
            }

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"


tool_dict = {
    "get_horoscope": get_horoscope,
    "get_base_conversion": get_base_conversion,
    "user_interaction": user_interaction,
    "calculate_google_maps_route": calculate_google_maps_route
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
        "description": "Use this function ONLY when you need to stop the execution loop to ask the user a question. The argument question should contain the clear, direct question you want to ask. The execution will pause until the user replies.",
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
    {
        "type": "function",
        "function":{
        "name": "calculate_google_maps_route",
        "description": "Function to calculate route between two places.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Point of origin used to calculate route.",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination used to calculate route.",
                },
                "transport_mode": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["BUS", "SUBWAY", "TRAIN", "LIGHT_RAIL", "RAIL"]
                },
                    "description": "Transit modes to allow"
                }
            },
            "required": ["origin", "destination","transport_mode"],
            "additionalProperties": False
        },
        }
    },
]

