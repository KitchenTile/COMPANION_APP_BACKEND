from typing import List
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

class TreeStructure(BaseModel):
    edges: list[NodeEdgeInfo]

class Actions(BaseModel):
    actions_array: list[str]

class Prevention(BaseModel):
    node_from: str
    node_to: str
    label: str
    itervetion: str

class Preventions(BaseModel):
    preventions: list[Prevention]

class Recovery(BaseModel):
    failure_mode: str
    label: str
    prevention: List[str] 
    correction: List[str] 
    severity: int 

class JourneyStep(BaseModel):
    node_from: str
    node_to: str
    label: str 
    risks: List[Recovery]

class TripAudit(BaseModel):
    steps: List[JourneyStep]

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
    risks: List[JustFailures]

class GraphWithFailures(BaseModel):
    steps: List[JourneyStepFailure]

#SINGLE GPT QUERY RETURNING JSON OBJECT WITH CORRECT PATH, FAILURES, INTERVENTIONS AND CORRECTIONS
def get_gpt_path_edges(maps_data, tools, model):
    print("Generating Graph...")
    
    system_prompt = f"""
        You are a "Resilient Route Architect" for an elderly-focused travel app. 
        Your goal is to transform Google Maps data into a robust, self-healing journey graph.

        ### INPUT:
        A list of Google Maps trip steps.

        ### OUTPUT OBJECTIVES:
        For every logical segment of the trip, you must generate a "Happy Path" edge and two "Failure Branch" objects.

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
            4. The "label" must give an explanation of how the failure state was reached (e.g. "trip and fall", "Missed Bus Stop"), avoid using the "node_to" as a "label".
            5. Keep labels short (max 5 words).
            6. For every edge, generate 2 failure objects.
    
        ### RULES FOR PROACTIVE PREVENTION GENERATION:
            1. Word the prevention from the application point of view (e.g., "Use voice navigation to keep user on track", "Remind user to be careful and watch path", "Use voice command to keep user on time") 
            2. Provide 1-3 short tips (max 8 words) to avoid this specific failure before it happens.
            3. If the prevention is related to arriving to a specific location earlier, phrase it as 'remind user to leave earlier' to get to the location you're referring to in time.

        ### RULES FOR REACTIVE CORRECTION GENERATION:
            1. Use tools available here: {tools}
            2. Decide ALL relevant tool to solve solve the situation.
            3. If no tool can solve the situaion, default to contacting the emergency contact.
            4. Do no return just the tool name, return a string of natural language (maximum 5 words) about the tool name (e.g. "ACTION: RECALCULATE ROUTE", "ACTION: CONTACT EMERGENCY CONTACT", "ACTION: EMAIL DOCTORS OFFICE")

        ### RULES FOR SEVERITY CALCULATION:
            1. Calculate Risk severity on a scale of 1-5.
        ### FORMATTING:
        - Use meaningful names for nodes (e.g., "Hendon Stop" not "Stop 1").
        - Keep all labels and descriptions concise for elderly users.
        """
    response = client.responses.parse(
        model=model,
        instructions=system_prompt,
        input = maps_data,
        text_format=TripAudit
    )

    content = response.output[1].content[0].text
    result = json.loads(content)
    
    if "edges" in result:
        return result["edges"]
    return result



#SINGLE GPT QUERY RETURNING JSON OBJECT WITH CORRECT PATH, FAILURES, INTERVENTIONS AND CORRECTIONS
def get_gpt_failure_nodes_general(maps_data, user_data, model):
    print("Generating Graph...")
    
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
            1. Calculate how probable it is for the user to fail in this particular way based on their vulnerabilities on a scale of 0-0.99.
            
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
    
    if "edges" in result:
        return result["edges"]
    return result



def get_gpt_correct_graph(maps_data, model):
    print("Generating Graph...")
    
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
    
    if "edges" in result:
        return result["edges"]
    return result


#SINGLE GPT QUERY RETURNING JSON OBJECT WITH CORRECT PATH, FAILURES, INTERVENTIONS AND CORRECTIONS
def get_gpt_failure_nodes(maps_data, current_step, user_data, model):
    print("Generating Graph...")
    
    system_prompt = f"""
        You are a "Resilient Route Architect" for an elderly-focused travel app. 
        Your goal is to generate up to four failure nodes for the current step the user is at. 

        ### INPUT:
        A list of Google Maps trip steps, the user's current step and the user's profile.

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
            4. The "label" must give an explanation of how the failure state was reached (e.g. "trip and fall", "Missed Bus Stop"), avoid using the "node_to" as a "label".
            5. Keep labels short (max 5 words).
            6. Failure nodes should not necessarily be tailored to the specific user's vulnerabilities.
    
        ### RULES FOR SEVERITY CALCULATION:
            1. Calculate Risk severity on a scale of 1-5.

        ### RULES FOR PROBABILITY CALCULATION:
            1. Calculate how probable it is for the user to fail in this particular way based on their vulnerabilities on a scale of 0-1.
            
        ### FORMATTING:
        - Use meaningful names for nodes (e.g., "Hendon Stop" not "Stop 1").
        - Keep all labels and descriptions concise for elderly users.
        """
    response = client.responses.parse(
        model=model,
        instructions=system_prompt,
        input = f"MAP DATA: {maps_data}, USER'S PROFILE: {user_data}",
        text_format=TripAudit
    )

    content = response.output[1].content[0].text
    result = json.loads(content)
    
    if "edges" in result:
        return result["edges"]
    return result