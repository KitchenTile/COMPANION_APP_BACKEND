from typing import List
from openai import OpenAI
from pydantic import BaseModel
import requests
import os
import dotenv


dotenv.load_dotenv()
client = OpenAI()

BASE_URL = "https://api.anticip8.ai/v1/anticip8ai"
HEADERS = {"X-API-KEY": os.getenv("ANTICIP8_KEY"), "X-API-SECRET": os.getenv("ANTICIP8_KEY_SECRET"), "Content-Type": "application/json"}


class NodeEdgeInfo(BaseModel):
    node_from: str
    node_to: str
    label: str

class TreeStructure(BaseModel):
    edges: List[NodeEdgeInfo]

class anticip8_route_prediction:
    def __init__(self, client):
        self.client = client

    def _generate_context(self, context_payload):
        try:
            ctx_resp = requests.post(f"{BASE_URL}/context/", headers=HEADERS, json=context_payload)
            ctx_id = ctx_resp.json()['id']
            print(ctx_id)
            return ctx_id
        except Exception as e:
            print(f"Error analysing context: {e}")
            return
    
    # use gpt to format the data from anticip8
    def _format_predictions(self, user_message):
        joint_user_answers = '/n'.join(user_message)

        print(joint_user_answers)

        response = client.responses.parse(
        model="gpt-5",
        input=joint_user_answers,
        instructions="""
                You are a data visualizer. 
                Convert the ranked predictions into a Tree Graph structure. 
                The 'node_from' should always be the user's current state (e.g., 'James (Home)'). 
                The 'node_to' is the predicted action (summarized in 3 words or less). 
                The 'label' is the action the user takes (eg. "walk", "Takes bus", etc.) using a maximum of 3 words.
            """,
        text_format=TreeStructure
        )

        print("user Rankings:")
            
        return response.output[1].content[0].text

    def run_anticip8_prediction(self, context_payload, actions: list[str] = None, gen_anticipations_num: int = 10, context_id: str = None):
        # if there's no context id, generate a new one based on context_payload
        if not context_id:
            context_id = self._generate_context(context_payload=context_payload)

        print("context id:")
        print(context_id)

        pred_payload = {"context": context_id, 'topn_anticip8_gen_actions': gen_anticipations_num, "anticipations_list": actions}
        response = requests.post(f"{BASE_URL}/anticipation/", headers=HEADERS, json=pred_payload).json()
        print(response)

        user_message = []

        for i, item in enumerate(response.get('ranked_anticipations', [])):
            user_message.append(f"Rank {i+1}: {item['action']}")
        
        print(user_message)

        print("GPT format")

        gpt_format = self._format_predictions(user_message)

        print(gpt_format)
    
    def generate_tree(self):
        pass
 


#create user profile (fixed)
profile_text = """
SUBJECT PROFILE: James elder male 72 years old
- MOBILITY: Walking speed is 50% slower than average. Uses a cane.
- RELATIONSHIPS: User has strong relationships with close family members. Main point of contact.
- ANXIETY: High anxiety about being late. High anxiety about getting lost, prefers the same route every time. Mild anxiety about falling.
- ALTERNATIVE TRAVEL: Has Uber app installed but rarely uses it due to cost concerns.

- PREVIOUS LOST HISTORY: {
    GENERAL TRAVEL DATA: "Out of their last 10 trips, user got lost seven times while changing busses. User never got lost while walking"
    SPECIFIC ROUTE LOST HISTORY: 
        DESCRIPTION: "The user got lost three times during this same trip"
        LOST DETAILS: [{lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }]
}
"""


# create context payload 
context_payload_new = {
    "subject": "James (Doctor Appt Journey)",
    "subject_profile_text": profile_text,
    
    "recent_history_text": (
        "USER STATUS: GPS places user at Home. Smart Watch detects high movement (user is getting ready). "
        "APPOINTMENT: Doctor at 10:00 AM (60 mins from now)."
        "APPOINTMENT DATA: {travel steps: 'The trip should take a total of 29 mins and cost around £1.75.\n\nHere are the steps:"
            "\nStep 1: Head east on Church Rd/A504 toward Parson St/B552\nContinue to follow A504. It should take 1 min (75 m)"
            "\nStep 2: Take Bus SL10 towards Harrow for 4 stops (15 mins), from Hendon / The Quadrant (Stop T) until Hendon Magistrates Court (Stop HP)."
            "\nStep 3: Head southeast on Edgware Rd/The Hyde/A5\nDestination will be on the left. It should take 1 min (86 m)"
            "\nStep 4: Take Bus 32 towards Kilburn Park for 9 stops (12 mins), from Hendon Magistrates Court (Stop HB) until Cricklewood Bus Garage (Stop BA).'"
            "}"
    ),
    
    "triggers_text": (
        "EXTERNAL DATA: "
        "1. APPOINTMENTS: User has regular doctors appointment today."
        "2. WEATHER: Heavy Rain (Walking to bus stop will be difficult). "
        "3. TRAFFIC: Roads are clear."
    )
}

# #user profile
profile_text = """
SUBJECT PROFILE: James (72 years old)
- MOBILITY: Walking speed is 50% slower than average. Uses a cane.
- RELATIONSHIPS: User has strong relationships with close family members. Main point of contact.
- ANXIETY: High anxiety about being late. High anxiety about getting lost, prefers the same route every time. Mild anxiety about falling 
- HABITS: User has weekly medical appoitments on Thursdays.
- ALTERNATIVE TRAVEL: Has Uber app installed but rarely uses it due to cost concerns.
"""

# create context payload 
context_payload = {
    "subject": "James (Doctor Appt Journey)",
    "subject_profile_text": profile_text,
    "recent_history_text": (
        "USER STATUS: GPS places user at Home. Smart Watch detects high movement (user is getting ready). "
        "APPOINTMENT: Doctor at 10:00 AM."
        """APPOINTMENT DATA: {travel steps: 'The trip should take a total of 29 mins and cost around £1.75.\n\nHere are the steps:
            "Step 1: Head east on Church Rd/A504 toward Parson St/B552\nContinue to follow A504. It should take 1 min (75 m)
            Step 2: Take Bus SL10 towards Harrow for 4 stops (15 mins), from Hendon / The Quadrant (Stop T) until Hendon Magistrates Court (Stop HP).
            Step 3: Head southeast on Edgware Rd/The Hyde/A5\nDestination will be on the left. It should take 1 min (86 m)
            Step 4: Take Bus 32 towards Kilburn Park for 9 stops (12 mins), from Hendon Magistrates Court (Stop HB) until Cricklewood Bus Garage (Stop BA).
            }"""
        "CURRENT TRAVEL STEP: {'Step 1: Head east on Church Rd/A504 toward Parson St/B552\nContinue to follow A504. It should take 1 min (75 m)'}"
    ),
    "triggers_text": (
        "EXTERNAL DATA: "
        "1. WEATHER: It's a nice summer morning with nice temperature and cool breeze."
        "2. APPOINTMENT: It's a thursday morning, user has an appointment today"
        "3. TRAFFIC: Roads are clear."
    )
}

actions = [
    "User will walk to the bus stop", 
    "User will get confused on his journey and will walk a differnet direction",
    "User will trip and fall on his way to the bus stop",
    "User will forget about his appointment and will not leave their home" 
]


anticip8 = anticip8_route_prediction(client)

anticip8.run_anticip8_prediction(context_payload, actions, 3)



# tree = AutoTreePlotter("My Automated Tree")
# tree.add_edge("Home", "Bus Stop", "catch bus")
# tree.add_edge("Home", "Tube Stn", "tube")
# tree.add_edge("Home", "Unknown", "walk")
# tree.add_edge("Bus Stop", "Hospital", "correct bus")
# tree.add_edge("Bus Stop", "Unknown", "wrong bus")


# tree.show()

# TODO:
# call GPT to decide actions based on situations, 
# use those actions to get anticip8 to rank recursevly run that to generate tree