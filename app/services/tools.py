import re
import requests
import dotenv
import os

from supabase import create_client

from app.services.anticip8.anticip8_manager import Anticip8RoutePredictor
from app.services.google_services.google_service_builder import GoogleServiceBuilder
from app.services.user_manager import CredentialManager
from app.services.google_services.gmail_service.gmail_client import GmailClient
from app.utils.helper_funcs import manage_db_journey

dotenv.load_dotenv()

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
def calculate_google_maps_route(origin: str, destination: str, transport_mode: list[str] = ["bus"]):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_API_KEY"),
        "X-Goog-FieldMask": "routes.*"
    }

    #check if a given location is an address or its coords
    def is_coords(location: str):
        x = re.search("^\s*([+-]?(?:90(?:\.0+)?|[0-8]?\d(?:\.\d+)?))\s*,?\s*([+-]?(?:180(?:\.0+)?|1[0-7]\d(?:\.\d+)?|\d{1,2}(?:\.\d+)?))\s*$", location)

        #return correct API dict
        if x:
            return {
                "location":{
                    "latLng":{
                        "latitude": location.split(',')[0],
                        "longitude": location.split(',')[1].strip()
                    }
                }
            }   
        else:
            return {
                "address": location
            }

    try:
        data = {
            "origin": is_coords(origin),
            "destination": is_coords(destination),
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

        print(data)

        #get encoded polyline for the location tracking
        encodedPolyline = route.get("legs", [])[0].get('polyline', {}).get('encodedPolyline')
        individualPolylines = [p.get("polyline", {}).get("encodedPolyline") for p in route.get("legs", [])[0].get('steps', {})]
        

        #get fastest route metadata
        route_summary = {
            "duration": route.get("localizedValues", {}).get("duration", {}).get("text"),
            "distance": route.get("localizedValues", {}).get("distance", {}).get("text"),
            "fare": route.get("localizedValues", {}).get("transitFare", {}).get("text", "N/A"),
            "steps": [],
            "raw_steps_data": []
        }

        # go through the route steps and add them to the summary
        for leg in route.get("legs", []):
            for index, step in enumerate(leg.get("steps", [])):

                # handle transit details
                if "transitDetails" in step:
                    transit = step["transitDetails"]
                    line = transit.get("transitLine", {})

                    step_instruction = (
                        f"Step {index + 1}: "
                        f"Take {line.get('vehicle', {}).get('name', {}).get('text')} "
                        f"{line.get('nameShort', line.get('name'))} "
                        f"towards {transit.get('headsign')} "
                        f"for {transit.get('stopCount')} stops "
                        f"({step.get('localizedValues', {}).get('staticDuration', {}).get('text')}), "
                        f"from {transit.get('stopDetails', {}).get('departureStop', {}).get('name')} "
                        f"until {transit.get('stopDetails', {}).get('arrivalStop', {}).get('name')}."
                    )
                    

                # handle walking details
                elif "navigationInstruction" in step:
                    nav = step["navigationInstruction"]

                    step_instruction = (
                        f"Step {index + 1}: {nav.get('instructions', 'Walk')}. "
                        f"It should take {step.get('localizedValues', {}).get('staticDuration', {}).get('text')} "
                        f"({step.get('localizedValues', {}).get('distance', {}).get('text')})"
                    )

                # individual step details needed for individual polyline AND anticip8
                route_summary["raw_steps_data"].append({
                    "index": index + 1,
                    "instruction": step_instruction, 
                    "polyline": step.get("polyline", {}).get("encodedPolyline")
                })
                
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
            "individualPolylines": individualPolylines,
            "action": "display_route"
            }

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"
    
def generate_route_with_preventions(origin, destination, journey_planner, user_id, task_id = None):

    print("printing origin and desstination")
    print(origin, destination)

    supabase = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_API_KEY")
    )

    try:
        response = supabase.table("users").select("*").eq("id", user_id).single().execute()
    except Exception as e:
        print(f"Error getting profile: {e}")

    if task_id != None:
        manage_db_journey(user_id=user_id, trip_id=task_id, origin=origin, destination=destination)

    user_profile = {"identity": response.data.get("identity"), "clinical_context": response.data.get("clinical_context"), "behavioral_history": response.data.get("behavioral_history")}

    journey_graph = journey_planner.calculate_route_wo_corrections(origin, destination, user_profile, "anticip8", "gpt-5")

    print(journey_planner)

    return journey_graph

    

#tool def
def send_email(user_id: str, to: str, subject: str, body: str, thread_id: str):

    scopes = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send", 
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    credential_manager = CredentialManager()

    gmail_service = GoogleServiceBuilder("gmail", "v1", credential_manager, user_id=user_id, scopes=scopes)

    gmail_client = GmailClient(user_id=user_id, credential_manager=credential_manager, scopes=scopes, service=gmail_service)

    try:
        email_body = gmail_client.create_email(to=to, subject=subject, body=body)

        print(email_body)

        sent_email = gmail_client.send_email(email_obj=email_body, thread_id=thread_id)

        print("sent email:")
        print(sent_email)

        return sent_email
        
    except Exception as e:
        return f"Gmail API error: {e}"



tool_dict = {
    "get_base_conversion": get_base_conversion,
    "user_interaction": user_interaction,
    'send_email': send_email,
    "generate_route_with_preventions": generate_route_with_preventions,
    "call_uber": None,
    "message_emergency_contact": None
}

#tools available for the model
tool_definitions = [
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
        "name": "send_email",
        "description": "Send an email via Gmail. ONLY use this tool after the user has explicitly consented to sending the email.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "The desired base to convert the number to",
                },
                "subject": {              
                    "type": "string",
                    "description": "The title or subject of the email",
                },
                "body": {              
                    "type": "string",
                    "description": "The email's body, do not include thread_id in email's body.",
                },
                "thread_id": {              
                    "type": "string",
                    "description": "The email's thread_id that connects it to the conversation.",
                },
            },
            "required": ["to", "subject", "body", 'thread_id'],
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
        "name": "generate_route_with_preventions",
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
            },
            "required": ["origin", "destination"],
            "additionalProperties": False
        },
        }
    },
]

