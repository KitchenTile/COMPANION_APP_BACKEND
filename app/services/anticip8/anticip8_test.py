import re
import time
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
 
 
class Anticip8RoutePredictor:
    def __init__(self):
        pass
    
    def _post_with_backoff(self, url, payload):
        while True:
            print(f"attempting call to {url}")
            response = requests.post(url, headers=HEADERS, json=payload)
            
            if response.status_code == 200 or response.status_code == 201:
                print("successful call")
                return response.json()

            try:
                error_data = response.json()
                detail_msg = error_data.get('detail', '')

                if response.status_code == 429 or 'throttled' in str(detail_msg).lower():
                    print(detail_msg)

                    match = re.search(r"available in (\d+) seconds", str(detail_msg))
                    if match:
                        wait_seconds = int(match.group(1)) + 5
                        time.sleep(wait_seconds)

                    else:
                        time.sleep(60)
                    continue
            except ValueError:
                pass  

            response.raise_for_status()

    def generate_context(self, context_payload):
        ctx_resp = self._post_with_backoff(f"{BASE_URL}/context/", context_payload)
        # ctx_resp = requests.post(f"{BASE_URL}/context/", headers=HEADERS, json=context_payload)
        return ctx_resp.get('id')

    def rank_step_options(self, context_id, context_payload, ranking_options, option_type):
        if not context_id:
            return "Error: No Context ID"

        pred_payload = {
            "context": context_id, 
            "topn_anticip8_gen_actions": 1,
            "anticipations_list": ranking_options
        }

        print(context_payload.get("recent_history_text"))

        try:
            # response = requests.post(f"{BASE_URL}/anticipation/", headers=HEADERS, json=pred_payload).json()
            response = self._post_with_backoff(f"{BASE_URL}/anticipation/", pred_payload)

            print("response")
            print(response)

            print(f"anticipations_list: {response.get("anticipations_list")}")

            # Get the top-ranked item
            ranked_items = response.get('ranked_anticipations', [])

            if not ranked_items:
                return None
            
            for anticipation in ranked_items:
                print(f"""
                    anticipation: {anticipation.get("action")}
                    probability: {anticipation.get("probability")}
                """)
                
            top_choice = ranked_items[0]
            print(f"Anticip8 selected top {option_type}: {top_choice['action']} (Prob: {top_choice['probability']})")

            # if the top item is created by anticip8, choose the top provided one
            if ranked_items[0]['source'] != "anticip8":
                return top_choice['action']
            else:
                return response.get('ranked_anticipations', [])[1]['action'] 
            
        except Exception as e:
            print(f"Error ranking options: {e}")
            return None




profile_text_complete = """
    SUBJECT PROFILE: James elder male 72 years old
    - MOBILITY: Walking speed is 50% slower than average. Uses a cane.
    - RELATIONSHIPS: User has strong relationships with close family members. Main point of contact.
    - ANXIETY: High anxiety about being late. High anxiety about getting lost, prefers the same route every time. Mild anxiety about falling.
    - ALTERNATIVE TRAVEL: Has Uber app installed but rarely uses it due to cost concerns.
    - PREVIOUS LOST HISTORY: {
        GENERAL TRAVEL DATA: "Out of their last 10 trips, user got lost seven times while changing busses. User never got lost while walking. Out of the last 10 journeys, user always reaches their destination BUT they take the wrong bus every time (!)."
        SPECIFIC ROUTE LOST HISTORY: 
            DESCRIPTION: The user got lost three times during this same trip
            LOST DETAILS: [{lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }, {lost_coords: (51.58148, -0.24444), origin: Home, destination: Doctors office, lost_step: 3, step_mode: walk }]
    }
    """
    # context payload
context_payload_complete = {
        "subject": "James (Doctor Appt Journey)",
        "subject_profile_text": profile_text_complete,
        
        "recent_history_text": (
            "APPOINTMENT: Doctor at 10:00 AM (60 mins from now)."
            """APPOINTMENT DATA: {travel steps: 'The trip should take a total of 29 mins and cost around £1.75.\n\nHere are the steps:
            "Step 1: Head east on Church Rd/A504 toward Parson St/B552\nContinue to follow A504. It should take 1 min (75 m)
            Step 2: Take Bus SL10 towards Harrow for 4 stops (15 mins), from Hendon / The Quadrant (Stop T) until Hendon Magistrates Court (Stop HP).
            Step 3: Head southeast on Edgware Rd/The Hyde/A5\nDestination will be on the left. It should take 1 min (86 m)
            }"""
            "CURRENT STEP: STEP 1: Head east on Church Rd/A504 toward Parson St/B552\nContinue to follow A504. It should take 1 min (75 m)"
        ),
        
        "triggers_text": (
            "EXTERNAL DATA: "
            "1. APPOINTMENTS: User has regular doctors appointment today."
            "2. WEATHER: Heavy Rain (Walking to bus stop will be difficult). "
            "3. TRAFFIC: Roads are clear."
            "USER IS ABOUT TO GET LOST IN ROUTE"
        )
    }


anticip8 = Anticip8RoutePredictor()

travel_information = """travel steps: The trip should take a total of 29 mins and cost around £1.75.\n\nHere are the steps:
            Step 1: Head east on Church Rd/A504 toward Parson St/B552\nContinue to follow A504. It should take 1 min (75 m)
            Step 2: Take Bus SL10 towards Harrow for 4 stops (15 mins), from Hendon / The Quadrant (Stop T) until Hendon Magistrates Court (Stop HP).
            Step 3: Head southeast on Edgware Rd/The Hyde/A5\nDestination will be on the left. It should take 1 min (86 m)"""
            

step_information = {
    'steps': [
        {'node_from': 'Start', 'node_to': 'Hendon / The Quadrant (Stop T)', 'label': 'Walk to Quadrant Stop', 'risks': [{'failure_mode': 'Lost En Route', 'label': 'Missed turn on A504', 'prevention': ['Use voice navigation to keep user on track', 'Announce landmarks early', 'Provide gentle reroute prompts'], 'correction': ['ACTION: RECALCULATE ROUTE', 'ACTION: CHECK IN WITH USER'], 'severity': 2},{'failure_mode': 'Injury From Fall', 'label': 'Tripped on uneven path', 'prevention': ['Remind user to be careful and watch path', 'Suggest cane or handrail', 'Warn about uneven pavement'], 'correction': ['ACTION: CONTACT EMERGENCY CONTACT', 'ACTION: CALL UBER'], 'severity': 4}]},
        # {'node_from': 'Hendon / The Quadrant (Stop T)', 'node_to': 'Hendon Magistrates Court (Stop HP)', 'label': 'Ride bus SL10, 4 stops', 'risks': [{'failure_mode': 'Missed Bus', 'label': 'Arrived after bus departed', 'prevention': ['Remind user to leave earlier to Quadrant Stop', 'Show live bus countdown', 'Enable vibration alerts'], 'correction': ['ACTION: RECALCULATE ROUTE', 'ACTION: CALL UBER'], 'severity': 2}, {'failure_mode': 'Missed Stop', 'label': 'Passed Magistrates Court stop', 'prevention': ['Announce stop names loudly', 'Vibrate before stop', 'Display big stop card'], 'correction': ['ACTION: RECALCULATE ROUTE', 'ACTION: CALL UBER'], 'severity': 2}]},
        # {'node_from': 'Hendon Magistrates Court (Stop HP)', 'node_to': 'Destination', 'label': 'Walk to Destination', 'risks': [{'failure_mode': 'Went Wrong Way', 'label': 'Turned away from A5', 'prevention': ['Use voice navigation to keep user on track', 'Announce left-side destination', 'Provide gentle reroute prompts'], 'correction': ['ACTION: RECALCULATE ROUTE', 'ACTION: CHECK IN WITH USER'], 'severity': 2}, {'failure_mode': 'Too Tired To Walk', 'label': 'Leg pain or fatigue', 'prevention': ['Suggest short rest spots', 'Offer slower pace mode', 'Estimate walk effort beforehand'], 'correction': ['ACTION: CALL UBER', 'ACTION: CHECK IN WITH USER'], 'severity': 3}]}
    ]
}



for index, step in enumerate(step_information.get("steps")):
    
    step_introduction = f"""User is currently on step: {index + 1}: going from: {step.get("node_from")} to: {step.get("node_to")}"""
    print(step_introduction)

    for risk in step.get("risks"):
        failure_point = f"""Failure point information: Next failure detected is {risk.get("failure_mode")}"""
        print(failure_point)
        preventions = f"""Preventions for this failure: {risk.get("prevention")}"""
        print(preventions)
        corrections = f"""Corrections for this failure: {risk.get("correction")}"""
        print(corrections)



        dynamic_history = (
                f"JOURNEY STATUS: User is currently at Step {index+1} of {len(step_information['steps'])}. "
                f"LOCATION: Moving from {step['node_from']} to {step['node_to']}. "
                f"PREVIOUS EVENTS: User has successfully completed steps 1 to {index}."
            )

        dynamic_triggers = (
            f"IMMEDIATE THREAT: {risk['failure_mode']} - {risk['label']}. "
            f"ENVIRONMENTAL CONTEXT: Heavy Rain (makes walking/cane use difficult). "
            f"USER STATE: Anxious about lateness."
        )

        current_context_payload = {
            "subject": "James (Elderly Traveler)",
            "subject_profile_text": profile_text_complete,
            "recent_history_text": dynamic_history,
            "triggers_text": dynamic_triggers
        }
        
        context_id = anticip8.generate_context(current_context_payload)

        # Rank Preventions 
        best_prevention = anticip8.rank_step_options(
            context_id,
            current_context_payload, 
            risk['prevention'], 
            option_type="prevention"
        )

        # Rank Corrections 
        # We might want to slightly tweak context here to say "User JUST failed"
        # but for now, using the same context is okay.
        best_correction = anticip8.rank_step_options(
            context_id,
            current_context_payload, 
            risk['correction'], 
            option_type="correction"
        )

        risk["best_prevention"] = best_prevention
        risk["best_correction"] = best_correction

        print(f"best prevention: {best_prevention}")
        print(f"best correction: {best_correction}")

print(step_information)


for risk in risk.get("risks"):
    anticip8_call = anticip8.rank_step_preventions(context_payload_complete, risk)

    print(anticip8_call)



print(anticip8.rank_step_preventions(context_payload_complete, step_information.get("steps")[0]))





for step in step_information.get("steps"):
    print(f"Analyzing step: {step.get("label")}")
    
    # Predict the most likely risk based on James's Profile (cane, anxiety, rain)
    most_likely_risk = anticip8.rank_step_corrections(context_payload_complete, step)

    print(most_likely_risk)
    









# class anticip8_route_prediction:
#     def __init__(self, client):
#         self.client = client

#     def _generate_context(self, context_payload):
#         try:
#             ctx_resp = requests.post(f"{BASE_URL}/context/", headers=HEADERS, json=context_payload)
#             ctx_id = ctx_resp.json()['id']
#             return ctx_id
#         except Exception as e:
#             print(f"Error analysing context: {e}")
#             return
    
#     # use gpt to format the data from anticip8
#     def _format_predictions(self, user_message):
#         joint_user_answers = '/n'.join(user_message)

#         print(joint_user_answers)

#         response = client.responses.parse(
#         model="gpt-5",
#         input=joint_user_answers,
#         instructions="""
#                 You are a data visualizer. 
#                 Convert the ranked predictions into a Tree Graph structure. 
#                 The 'node_from' should always be the user's current state (e.g., 'James (Home)'). 
#                 The 'node_to' is the predicted action (summarized in 3 words or less). 
#                 The 'label' is the action the user takes (eg. "walk", "Takes bus", etc.) using a maximum of 3 words.
#             """,
#         text_format=TreeStructure
#         )

#         print("user Rankings:")
            
#         return response.output[1].content[0].text

#     def run_anticip8_prediction(self, context_payload, actions: list[str] = None, gen_anticipations_num: int = 10, context_id: str = None):
#         # if there's no context id, generate a new one based on context_payload
#         if not context_id:
#             context_id = self._generate_context(context_payload=context_payload)

#         print("context id:")
#         print(context_id)

#         pred_payload = {"context": context_id, 'topn_anticip8_gen_actions': gen_anticipations_num, "anticipations_list": actions}
#         response = requests.post(f"{BASE_URL}/anticipation/", headers=HEADERS, json=pred_payload).json()
#         print(response)

#         user_message = []


#         for i, item in enumerate(response.get('ranked_anticipations', [])):
#             user_message.append(f"Rank {i+1}: {item['action']}")

#         print(user_message)
