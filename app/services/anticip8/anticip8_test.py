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
                
                if isinstance(error_data, dict):
                    detail_msg = error_data.get('detail', str(error_data))
                else:
                    detail_msg = str(error_data)

            except ValueError:
                detail_msg = response.text

            if response.status_code == 429 or 'throttled' in str(detail_msg).lower():
                print(f"Throttled: {detail_msg}")
                
                match = re.search(r"available in (\d+) seconds", str(detail_msg))
                if match:
                    wait_seconds = int(match.group(1)) + 5
                    print(f"waiting for {wait_seconds} seconds")
                    time.sleep(wait_seconds)
                else:
                    time.sleep(60)
                continue

            print(f"API REJECTED REQUEST ({response.status_code}): {detail_msg}")
            response.raise_for_status()

    def generate_context(self, context_payload):
        ctx_resp = self._post_with_backoff(f"{BASE_URL}/context/", context_payload)
        # ctx_resp = requests.post(f"{BASE_URL}/context/", headers=HEADERS, json=context_payload)
        return ctx_resp.get('id')

    def rank_step_options(self, context_id, ranking_options, option_type):
        if not context_id:
            return "Error: No Context ID"

        pred_payload = {
            "context": context_id, 
            "topn_anticip8_gen_actions": 1,
            "anticipations_list": ranking_options
        }

        try:
            # response = requests.post(f"{BASE_URL}/anticipation/", headers=HEADERS, json=pred_payload).json()
            response = self._post_with_backoff(f"{BASE_URL}/anticipation/", pred_payload)

            print("response")
            print(response)

            print(f"anticipations_list: {response.get('anticipations_list')}")

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

            # # if the top item is created by anticip8, choose the top provided one
            if top_choice['source'] != "Anticip8":
                return top_choice['action']
            else:
                first_own_action = ranked_items[1]['action']
                print(first_own_action)
                return first_own_action
        
        except Exception as e:
            print(f"Error ranking options: {e}")
            return None
    
    def get_anticip8_failures(self, context_id):
        if not context_id:
            return "Error: No Context ID"

        pred_payload = {
            "context": context_id, 
            "topn_anticip8_gen_actions": 4,
        }

        try:
            response = self._post_with_backoff(f"{BASE_URL}/anticipation/", pred_payload)

            print("response")
            print(response)

            print(f"anticipations_list: {response.get('anticipations_list')}")

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
            print(f"Anticip8 selected: {top_choice['action']} (Prob: {top_choice['probability']})")

            return ranked_items
        
        except Exception as e:
            print(f"Error ranking options: {e}")
            return None
        
    def calculate_new_probability(self, current_step, anticipation_list, context_id):
        if not context_id:
            return "Error: No Context ID"
                
        pred_payload = {
            "context": context_id, 
            "topn_anticip8_gen_actions": 1,
            "anticipations_list": anticipation_list
        }

        try:
            response = self._post_with_backoff(f"{BASE_URL}/anticipation/", pred_payload)

            print("response")
            print(response)

            print(f"anticipations_list: {response.get('anticipations_list')}")

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
            print(f"Anticip8 selected: {top_choice['action']} (Prob: {top_choice['probability']})")

            return ranked_items
        
        except Exception as e:
            print(f"Error ranking options: {e}")
            return None
            

    def anticip8_call(self, context_id, anticipation_list = [], anticip8_gen_number = 1):
        if not context_id:
            return "Error: No Context ID"

        pred_payload = {
            "context": context_id, 
            "topn_anticip8_gen_actions": anticip8_gen_number,
            "anticipations_list": anticipation_list
        }

        try:
            response = self._post_with_backoff(f"{BASE_URL}/anticipation/", pred_payload)

            print("response")
            print(response)

            print(f"anticipations_list: {response.get('anticipations_list')}")

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
            print(f"Anticip8 selected: {top_choice['action']} (Prob: {top_choice['probability']})")

            return ranked_items
        
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
