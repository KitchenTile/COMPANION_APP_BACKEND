from app.services.anticip8.anticip8_test import Anticip8RoutePredictor
from app.services.tools import calculate_google_maps_route
from app.utils.tree_plotter import get_gpt_path_edges


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

class JourneyPlanner():
    def __init__(self, user_id, tools):
        self.user_id = user_id
        self.tools = tools

    def _get_travel_steps(self, origin, destination):
        self.travel_steps_from_google = calculate_google_maps_route(origin, destination, ["bus"])

    def calculate_route(self, origin, destination, model):
        if not self.travel_steps_from_google:
            self._get_travel_steps(origin, destination)
            
        step_information = get_gpt_path_edges(self.travel_steps_from_google, self.tools)

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
                    risk['prevention'], 
                    option_type="prevention"
                )

                # Rank Corrections 
                # We might want to slightly tweak context here to say "User JUST failed"
                # but for now, using the same context is okay.
                best_correction = anticip8.rank_step_options(
                    context_id,
                    risk['correction'], 
                    option_type="correction"
                )

                risk["best_prevention"] = best_prevention
                risk["best_correction"] = best_correction

                print(f"best prevention: {best_prevention}")
                print(f"best correction: {best_correction}")

            print(step_information)
            return step_information

