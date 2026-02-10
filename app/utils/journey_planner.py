import json
import ssl

import urllib
from app.services.anticip8.anticip8_test import Anticip8RoutePredictor
from app.services.tools import calculate_google_maps_route
from app.utils.tree_plotter import get_gpt_path_edges


profile_text_complete = """
    SUBJECT PROFILE: James elder male 72 years old.
    - MOBILITY: Walking speed is 50% slower than average. Uses a cane.
    - RELATIONSHIPS: User has strong relationships with close family members. Main point of contact.
    - ANXIETY: High anxiety about being late. High anxiety about getting lost, prefers the same route every time. Mild anxiety about falling.
    - ALTERNATIVE TRAVEL: Has Uber app installed but rarely uses it due to cost concerns.
    - PREVIOUS LOST HISTORY: {
        GENERAL TRAVEL DATA: "Out of their last 10 trips, user got lost seven times while changing busses. User never got lost while walking. User positively reacts to being gently rerouted through voice command. User prefers not being suggested to order an uber."
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
            f"ACTION HISTORY: James has a 100% success rate with Uber, 20% with manual re-routing."
            "USER IS ABOUT TO GET LOST IN ROUTE"
        )
    }

def get_london_weather():
    url = "https://api.open-meteo.com/v1/forecast?latitude=51.5074&longitude=-0.1278&current=temperature_2m,precipitation&timezone=auto"
    
    context = ssl._create_unverified_context()
    
    try:
        with urllib.request.urlopen(url, context=context) as response:
            data = json.loads(response.read().decode())
            
            result = {
                "temperature": f"{data['current']['temperature_2m']}°C",
                "precipitation": f"{data['current']['precipitation']} mm"
            }
            return json.dumps(result, indent=4)
            
    except Exception as e:
        return json.dumps({"error": str(e)})

class JourneyPlanner():
    def __init__(self, tools):
        self.tools = tools
        self.travel_steps_from_google = None

    def _get_travel_steps(self, origin, destination):
        travel_steps_from_google = calculate_google_maps_route(origin, destination, ["bus"])
        self.travel_steps_from_google = travel_steps_from_google.get("text")

    def calculate_route(self, origin, destination, model):
        if not self.travel_steps_from_google:
            print(f"calculating travel steps from {origin} to {destination}")
            self._get_travel_steps(origin, destination)

        print(self.travel_steps_from_google)
            
        print("calulating graph based on travel steps")
        step_information = get_gpt_path_edges(self.travel_steps_from_google, self.tools)

        print(f"Graph: {step_information}")
        print("Initiating anticip8")
        anticip8 = Anticip8RoutePredictor()

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

                current_weather = get_london_weather()

                dynamic_history = (
                        f"JOURNEY STATUS: User is currently at Step {index+1} of {len(step_information['steps'])}. "
                        f"LOCATION: Moving from {step['node_from']} to {step['node_to']}. "
                        f"PREVIOUS EVENTS: User has successfully completed steps 1 to {index}."
                    )

                dynamic_triggers = (
                    f"IMMEDIATE THREAT: {risk['failure_mode']} - {risk['label']}. "
                    f"ENVIRONMENTAL CONTEXT: Current temperature at user's location is {current_weather.get("temperature")}. Current precipitation level at user's location is {current_weather.get("precipitation")}  "
                    f"USER STATE: Anxious about lateness."
                    f"ACTION HISTORY: James has a 100% success rate with Uber, 20% with manual re-routing."

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
                    risk['prevention'], 
                    option_type="prevention"
                )

                # add extra line to trigger text to indicate the user had an issue
                current_context_payload["triggers_text"] += f" CRITICAL: {risk['failure_mode']} has occurred!"
                crisis_context_id = anticip8.generate_context(current_context_payload)

                # Rank Corrections 
                best_correction = anticip8.rank_step_options(
                    crisis_context_id,
                    risk['correction'], 
                    option_type="correction"
                )

                risk["best_prevention"] = best_prevention
                risk["best_correction"] = best_correction

                print(" -- ")
                print(f"best prevention: {best_prevention}")
                print(f"best correction: {best_correction}")
                print(" -- ")


        print(step_information)
        return step_information

