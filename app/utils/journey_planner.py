import json
import ssl

import urllib
from app.services.tools import calculate_google_maps_route
from app.utils.tree_plotter import get_gpt_correct_graph, get_gpt_failure_nodes_general, get_gpt_new_probabilities, get_gpt_preventions, gpt_formatted_nodes

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
            return result
            
    except Exception as e:
        return json.dumps({"error": str(e)})
    
class JourneyPlanner():
    def __init__(self, tools, anticip8):
        self.tools = tools
        self.anticip8 = anticip8
        self.travel_steps_from_google = None

    def _get_travel_steps(self, origin, destination):
        travel_steps_from_google = calculate_google_maps_route(origin, destination, ["bus"])
        self.travel_steps_from_google = travel_steps_from_google

        

    def anticip8_graph_with_failures(self, correct_graph_path, user_profile):
        for index, step in enumerate(correct_graph_path.get("steps")):
            if index+1 > 1:
                previous_events = f"User has successfully completed steps 1 to {index + 1}."
            else:
                previous_events = f"User is about to start their journey's first step."

            
            user_profile_string = f"{user_profile}"

            
            dynamic_history = (
                f"JOURNEY STATUS: User is currently at Step {index+1} of {len(correct_graph_path.get('steps'))}. "
                f"LOCATION: Moving from {step['node_from']} to {step['node_to']} by {step['label']}. "
                f"RULES FOR ANTICIP8: GIVE NEGATIVE ACTIONS THAT WOULD DERAIL THE USER FROM THEIR CURRENT PATH. DO NOT INCLUDE ANY OTHER ACTION IN THE PREDICTED ANTICIPATIONS OTHER THAN THESE DERAIL ACTIONS"
            )

            dynamic_triggers = (
                f"PREVIOUS EVENTS: {previous_events}"
            )

            current_context_payload = {
                "subject": "Negative situations for user's journey",
                "subject_profile_text": user_profile_string,
                "recent_history_text": dynamic_history,
                "triggers_text": dynamic_triggers
            }

            context_id = self.anticip8.generate_context(current_context_payload)

            anticip8_failures = self.anticip8.anticip8_call(context_id, anticipation_list=[step['label']], anticip8_gen_number = 4)

            print(anticip8_failures)

            anticip8_failure_modes = []
            for index, risk in enumerate(anticip8_failures):
                if risk.get("action") != step['label']:
                    anticip8_failure_modes.append(risk.get('action'))
                else:
                    step['probability'] = risk.get("probability")

            formatted_nodes = gpt_formatted_nodes(step, anticip8_failure_modes, "gpt-5")

            print(formatted_nodes)

            for index, node in enumerate(formatted_nodes.get("risks")):
                node['probability'] = anticip8_failures[index].get("probability")


            step['risks'] = formatted_nodes.get('risks')
        
        return correct_graph_path


    def calculate_new_probability(self, graph, user_profile):
        # caluclate how the robability changes with each prevention
        for step in graph.get("steps"):
            detailed_preventions = []

            for prevention in step.get("preventions"):
                new_probabilities = get_gpt_new_probabilities(step, prevention, user_profile, "gpt-5-nano")

                print(new_probabilities)
                print("new_probabilities")
            
                # Map the new probabilities to the failure modes
                risk_impacts = {}
                #add correct route probability change
                risk_impacts[step.get("node_to")] = new_probabilities.get("probability")

                for risk in new_probabilities.get("risks", []):
                    risk_impacts[risk.get("failure_mode")] = risk.get("probability")

                # Store the prevention label along with its specific probability adjustments
                detailed_preventions.append({
                    "label": prevention,
                    "adjusted_probabilities": risk_impacts
                })

                print("detailed preventions")
                print(detailed_preventions)
            
            step["preventions"] = detailed_preventions

        return graph
    

    def anticip8_calculate_new_probability(self, correct_graph_path, user_profile):
        for index, step in enumerate(correct_graph_path.get("steps")):
            detailed_preventions = []

            if index+1 > 1:
                previous_events = f"User has successfully completed steps 1 to {index + 1}."
            else:
                previous_events = f"User is about to start their journey's first step."

            
            user_profile_string = f"{user_profile}"

            for prevention in step.get("preventions"):

            
                dynamic_history = (
                    f"JOURNEY STATUS: User is currently at Step {index+1} of {len(correct_graph_path.get('steps'))}. "
                    f"LOCATION: Moving from {step['node_from']} to {step['node_to']} by {step['label']}. "
                )

                dynamic_triggers = (
                    f"PREVIOUS EVENTS: {previous_events}, ACTION TAKEN: {prevention}"
                )

                current_context_payload = {
                    "subject": "User's journey probability after taking an action",
                    "subject_profile_text": user_profile_string,
                    "recent_history_text": dynamic_history,
                    "triggers_text": dynamic_triggers
                }

                context_id = self.anticip8.generate_context(current_context_payload)

                action_list = [step['node_to']]

                for risk in step.get("risks"):
                    action_list.append(risk.get("failure_mode"))
                    
                print("action_list")
                print(action_list)

                anticip8_node_recalculation = self.anticip8.anticip8_call(context_id, anticipation_list=action_list, anticip8_gen_number = 1)

                print("recalculations:")
                print(anticip8_node_recalculation)

                risk_impacts = {}
                for anticipation in anticip8_node_recalculation:
                    if anticipation["source"] != "Anticip8":
                        risk_impacts[anticipation["action"]] = anticipation["probability"]

                detailed_preventions.append({
                    "label": prevention,
                    "adjusted_probabilities": risk_impacts
                })

                
            step["preventions"] = detailed_preventions
        
        return correct_graph_path
    

    def add_best_preventions(self, graph):
        for step in graph['steps']:
            best_prevention = None
            highest_success_prob = 0
            success_node = step['node_to']

            for prevention in step.get('preventions', []):
                success_prob = prevention['adjusted_probabilities'].get(success_node)
                if success_prob > highest_success_prob:
                    highest_success_prob = success_prob
                    best_prevention = prevention
            
            # Strip away the array and just attach the best one to the step
            step['best_prevention'] = best_prevention 

            print("Best Prevention")
            print(step["best_prevention"])

        return graph
    
    def calculate_route_wo_corrections(self, origin, destination, user_profile, model, probability_model):
        if not self.travel_steps_from_google:
            print(f"calculating travel steps from {origin} to {destination}, using {model}")
            self._get_travel_steps(origin, destination)
            print(self.travel_steps_from_google.get("text"))

        print(self.travel_steps_from_google)
        # turn google maps data into graph like structure
        correct_graph_path = get_gpt_correct_graph(self.travel_steps_from_google.get("text"), "gpt-5")

        path_with_failures = {}
        if model == "anticip8":
            # this is the anticip8 generated graph with error nodes
            path_with_failures = self.anticip8_graph_with_failures(correct_graph_path, user_profile)

        else:
            # add failure nodes
            path_with_failures = get_gpt_failure_nodes_general(correct_graph_path, user_profile, "gpt-5")

        #add preventions
        path_with_preventions = get_gpt_preventions(path_with_failures, "gpt-5")

        print("path with preventions:")
        print(path_with_preventions)
        print()
        print("calculating prevention weight on nodes")

        graph_with_new_weights = {}
        if probability_model == "anticip8":
            graph_with_new_weights = self.anticip8_calculate_new_probability(path_with_preventions, user_profile)

        else:
            graph_with_new_weights = self.calculate_new_probability(path_with_preventions, user_profile)

        final_graph = self.add_best_preventions(graph_with_new_weights)

        print(final_graph)

        return {
            "graph": final_graph,
            "text": self.travel_steps_from_google.get("text"),
            "polyline": self.travel_steps_from_google.get("polyline"),
            "individualPolylines": self.travel_steps_from_google.get("individualPolylines"),
            "action": "display_route"
        }