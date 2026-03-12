from typing import List, Literal
from dotenv import load_dotenv
import networkx as nx
import json
from openai import OpenAI
from pydantic import BaseModel


#load env file
load_dotenv()

# Initialize the client
client = OpenAI()

class NodeEdgeInfo(BaseModel):
    node_from: str
    node_to: str
    label: str
    mapped_raw_steps: list[int]

# class Prevention(BaseModel):
#     node_from: str
#     node_to: str
#     label: str
#     itervetion: str

class Prevention(BaseModel):
    label: str
    action_text: str
    action_voice: str
    trigger_timing: Literal["AT_STEP_START", "MID_STEP", "AT_STEP_END"]

class NodeEdgeInfoArray(BaseModel):
    steps: List[NodeEdgeInfo]

class JustFailures(BaseModel):
    failure_mode: str
    label: str
    severity: int
    probability: float

class JourneyStepFailure(BaseModel):
    node_from: str
    node_to: str
    label: str 
    mapped_raw_steps: list[int]
    probability: float
    risks: List[JustFailures]

class GraphWithFailures(BaseModel):
    steps: List[JourneyStepFailure]

class JourneyStepFailureAndPreventions(BaseModel):
    node_from: str
    node_to: str
    label: str
    mapped_raw_steps: list[int]
    probability: float
    risks: List[JustFailures]
    preventions: List[Prevention]

class GraphWithFailuresAndPreventions(BaseModel):
    steps: List[JourneyStepFailureAndPreventions]

class Risk(BaseModel):
    failure_mode: str
    label: str

class RisksArray(BaseModel):
    risks: List[Risk]

#Generates graph with correct steps and failure modes
def get_gpt_failure_nodes_general(maps_data, user_data, model):
    print("Generating gpt graph with failures...")
    
    system_prompt = f"""
        You are a "Resilient Route Architect" for an elderly-focused travel app. 
        Your goal is to transform Google Maps data into a graph, that detects possible failures based on a user's profile.

        ### INPUT:
        A list of Google Maps trip steps.

        ### OUTPUT OBJECTIVES:
        For every logical segment of the trip, you must generate a "Happy Path" edge and up to four "Failure Branch" objects.

        ### RULES FOR HAPPY PATH GENERATION:
             1. Summarize small consecutive walking steps into a single meaningful edge (e.g., "Walk 5 mins to Station").
             2. Keep Transit steps distinct.
             3. Ensure the graph is continuous (the 'node_to' of step A must be the 'node_from' of step B).
             4. Start the first node as "Start" and the last node as "Destination".
             5. Ensure step 'node_to' and 'node_from' have meaninful names instead of index numbers or letters, if the user is about to take a bus, indicate they are going from bus stop to bus stop.
             6. Ignore the time each step takes.
             7. Keep to a maximum of 5 words.

        ### RULES FOR FAILURE BRANCH OBJECT GENERATION:
            1. The 'node_from' must match a node from the input.
            2. The 'node_to' must be a new, unique failure state (e.g., "Missed Bus", "Lost Wallet").
            3. If the step involves a Bus/Train, the failure must be transit-related (e.g., "Bus broke down").
            4. The "label" must give an explanation of how the failure state was reached (e.g. "trip and fall", "Missed Bus Stop"), avoid using the "node_to", "node_from" OR the failure point itself as a "label" or included in the "label".
            5. Keep labels short (max 5 words).
            6. Failure nodes should not necessarily be tailored to the specific user's vulnerabilities.
    

        ### RULES FOR SEVERITY CALCULATION:
            1. Calculate Risk severity on a scale of 1-5.

        ### RULES FOR PROBABILITY CALCULATION:
            1. Calculate how probable it is for the user to fail in this particular way based on their vulnerabilities on a scale of 1-10. Make sure to ALSO include the probability for the user to go in the correct following node based on their profile.
            
        ### FORMATTING:
        - Use meaningful names for nodes (e.g., "Hendon Stop" not "Stop 1").
        - Keep all labels and descriptions concise for elderly users.
        """
    response = client.responses.parse(
        model=model,
        instructions=system_prompt,
        input = f"MAP DATA: {maps_data}, USER'S PROFILE: {user_data}",
        text_format=GraphWithFailures
    )

    content = response.output[1].content[0].text
    result = json.loads(content)

    return result


# generate a correct path from google maps steps
def get_gpt_correct_graph(maps_data, model):
    print("Generating graph from maps data...")
    
    system_prompt = f"""
        You are a "Resilient Route Architect" for an elderly-focused travel app. 
        Your goal is to transform Google Maps data into a graph.

        ### INPUT:
        A list of Google Maps trip steps.

        ### OUTPUT OBJECTIVES:
        For every logical segment of the trip, you must generate a "Happy Path".

        ### RULES FOR HAPPY PATH GENERATION:
            1. Summarize small consecutive walking steps into a single meaningful edge (e.g., "Walk 5 mins to Station").
            2. Keep Transit steps distinct.
            3. Ensure the graph is continuous (the 'node_to' of step A must be the 'node_from' of step B).
            4. Start the first node as "Start" and the last node as "Destination".
            5. Ensure step 'node_to' and 'node_from' have meaninful names instead of index numbers or letters, if the user is about to take a bus, indicate they are going from bus stop to bus stop.
            6. Ignore the time each step takes.
            7. Keep to a maximum of 5 words.
            8.8. For each logical edge, provide an array of integers in 'mapped_raw_steps' representing the exact Step numbers from the input text that are summarized into this edge (e.g., if you summarized Steps 1, 2, and 3, output [1, 2, 3]).

        ### FORMATTING:
        - Use meaningful names for nodes (e.g., "Hendon Stop" not "Stop 1").
        - Keep all labels and descriptions concise for elderly users.
        """
    response = client.responses.parse(
        model=model,
        instructions=system_prompt,
        input = f"MAPS DATA: {maps_data}",
        text_format=NodeEdgeInfoArray
    )

    content = response.output[1].content[0].text
    result = json.loads(content)

    return result

#Based on maps with failures, generate preventions
def get_gpt_preventions(maps_data, model):
    print("Generating gpt graph with preventions...")
    
    system_prompt = f"""
        You are a "Resilient Route Architect" for an elderly-focused travel app. 
        Your goal is to given Google Maps data in graph ready form, add preventions that would allow prevent the user from falling into the "failure_mode" nodes.
        This way you would effectively allow the user to keep on their correct path.

        ### INPUT:
        A list of travel objects with the shape: node_from: A travel step origin. node_to: A trave step destination. label: An explanation of how to get from node_from to node_to. Risks: An array of risks objects explaining what could happen to deviate the user from their current path.

        ### OUTPUT OBJECTIVES:
        For every logical segment of the trip, you must generate a up to three preventions that would prevent the user from falling into these risk scenarios.

        ### RULES FOR PROACTIVE PREVENTION GENERATION:
            1. Word the prevention from the application point of view (e.g., "Use voice navigation to keep user on track", "Remind user to be careful and watch path", "Use voice command to keep user on time") 
            2. Provide 1-3 short preventions (max 8 words) to avoid specific failures before they happen.
            3. If the prevention is related to arriving to a specific location earlier, phrase it as 'remind user to leave earlier' to get to the location you're referring to in time.
            4. Provide the 'action_voice' (The exact sentence the TTS will read, will be directly spoken to the user).
            5. Provide the 'action_text' (The text displayed in the UI, make it 8 words or less, will be directly shown to the user).
            6. Define 'trigger_timing' (When should the app trigger this? At the start of the step, or halfway through?).
        """
    
    response = client.responses.parse(
        model=model,
        instructions=system_prompt,
        input = f"Map data: {maps_data}",
        text_format=GraphWithFailuresAndPreventions
    )

    content = response.output[1].content[0].text
    result = json.loads(content)

    return result


#Changes probabilities based on preventions
def get_gpt_new_probabilities(current_step, prevention, user_data, model):
    print("Generating gpt graph with failures...")
    
    system_prompt = f"""
        You are a "Resilient Route Architect" for an elderly-focused travel app. 
        Your goal is to recalculate failure and correct path probability based a possible prevention against failure situations. 

        ### INPUT:
        The current journey step the user is in, the user information, and one action taken to prevent the user from straying from their path.

        ### OUTPUT OBJECTIVES:
        The output should be the same journey step with the only change being the new probabilities (if applicable) wether node_to probability or a risk probability. If the prevention applied DO NOT affect a particular failure probability or correct path, return the same value.

        ### RULES FOR PROBABILITY ADJUSTMENT:
             1. Based on the action taken, RECALCULATE the probability value of each of the risks (and correct path) inside the journey step.
             2. The next step's correct path is the "node_to" property. To recalculate the correct node probability, change the current step's "probability" property.
             3. If a particular risk is not affected by the prevention action, return the same value.
             4. Base your adjustments on the user's profile and their vulnerabilities.
        """
    response = client.responses.parse(
        model=model,
        instructions=system_prompt,
        input = f"CURRENT STEP: {current_step}, USER'S PROFILE: {user_data}, ACTION TAKEN: {prevention}",
        text_format=JourneyStepFailureAndPreventions
    )

    content = response.output[1].content[0].text
    result = json.loads(content)

    return result

#format anticip8's failure nodes
def gpt_formatted_nodes(map_data, failure_nodes, model):
            
    system_prompt = f"""
        You are a "Resilient Route Architect" for an elderly-focused travel app. 
        Your goal is to format incoming data into a graph node in a way that fits the existing travel graph nodes. 

        ### INPUT:
        A list of Google Maps trip steps and a specific failure situation in natural language.

        ### OUTPUT OBJECTIVES:
        An array of risk objects

        ### RULES FOR RISK FORMATTING:
             1. Summarize the natural language input into the core failure mode using less than 5 words (e.g., 'Missed Bus 32', 'Panick Attack', 'Trip and Fall').
             2. The "label" must give an explanation of how the failure state was reached (e.g. "Uneven pavement hazard", "Missed Right Turn"), avoid using the "node_to" as a "label".
             3. Keep all labels and descriptions concise for elderly users.
           """
    response = client.responses.parse(
        model=model,
        instructions=system_prompt,
        input = f"MAP DATA: {map_data}, FAILURE NODES: {failure_nodes}",
        text_format=RisksArray
    )

    content = response.output[1].content[0].text
    result = json.loads(content)

    return result