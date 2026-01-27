from typing import List
from dotenv import load_dotenv
import plotly.graph_objects as go
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
    edges: List[NodeEdgeInfo]

class actions(BaseModel):
    actions_array: list[str]


class AutoTreePlotter:
    def __init__(self, title="Route Diagram"):
        self.G = nx.DiGraph()
        self.title = title

    def add_edge(self, parent, child, label=""):
        """Add a connection. Nodes are created automatically."""
        self.G.add_edge(parent, child, label=label)

    def show(self):
        # calculate Layout with helper function
        pos = self._get_hierarchy_pos(self.G)

        node_x = []
        node_y = []
        node_text = []
        
        for node, (x, y) in pos.items():
            node_x.append(x)
            node_y.append(y)
            node_text.append(str(node))

        # create the Plot
        fig = go.Figure()

        # edges
        for start, end in self.G.edges():
            x0, y0 = pos[start]
            x1, y1 = pos[end]
            label = self.G.edges[start, end].get('label', '')

            fig.add_annotation(
                x=x1, y=y1, ax=x0, ay=y0,
                xref='x', yref='y', axref='x', ayref='y',
                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2,
                arrowcolor="#555",
                standoff= 32,
                startstandoff= 32
            )

            # label
            if label:
                fig.add_annotation(
                    x=(x0 + x1) / 2, y=(y0 + y1) / 2,
                    text=label, showarrow=False,
                    bgcolor="white", font=dict(size=12, color="blue")
                )

        # nodes
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            text=node_text,
            textposition="middle center",
            marker=dict(size=60, color='white', line=dict(width=2, color='black')),
            hoverinfo='text'
        ))

        fig.update_layout(
            title=self.title,
            showlegend=False,
            plot_bgcolor='white',
            margin=dict(l=200, r=200, t=40, b=20),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        
        # fig.show()
        fig.write_html("tree.html")


    def _get_hierarchy_pos(self, G, root=None, width=1, vert_gap=0.2, xcenter=0.5):
        if root is None:
            # Find the root
            roots = [n for n, d in G.in_degree() if d == 0]
            root = roots[0] if roots else list(G.nodes())[0]

        def _hierarchy_pos(G, root, width=1., vert_gap=0.5, vert_loc=1, xcenter=1, pos=None, parent=None):
            if pos is None:
                pos = {root: (xcenter, vert_loc)}
            else:
                pos[root] = (xcenter, vert_loc)
            children = list(G.neighbors(root))
            if not isinstance(G, nx.DiGraph) and parent is not None:
                children.remove(parent)  
            if len(children) != 0:
                dx = width / len(children) 
                nextx = xcenter - width/2 - dx/2
                for child in children:
                    nextx += dx
                    pos = _hierarchy_pos(G, child, width=dx, vert_gap=vert_gap, 
                                         vert_loc=vert_loc-vert_gap, xcenter=nextx,
                                         pos=pos, parent=root)
            return pos

        return _hierarchy_pos(G, root, width, vert_gap, 0, xcenter)

data ='The trip should take a total of 1 hour 3 mins and cost around £1.75.\n\nHere are the steps:\nStep 1: Head northwest on Village Rd toward Hendon Ave. It should take 3 mins (0.3 km)\nStep 2: Turn left toward Holders Hill Rd/B552. It should take 2 mins (0.1 km)\nStep 3: Turn right toward Holders Hill Rd/B552. It should take 1 min (8 m)\nStep 4: Turn right onto Holders Hill Rd/B552\nDestination will be on the left. It should take 1 min (42 m)\nStep 5: Take Bus 240 towards Edgware for 22 stops (27 mins), from Hendon Cemetery until Edgware Station (Stop G).\nStep 6: Take Bus 142 towards Brent Cross for 15 stops (20 mins), from Edgware Station (Stop G) until Sheaveshill Avenue (Stop CG).\nStep 7: Head southeast on Edgware Rd/A5 toward Varley Parade\nDestination will be on the right. It should take 2 mins (0.2 km)'

def get_edges_from_gpt(maps_data):
    
    system_prompt = """
    You are a route summarizer. You convert Google Maps JSON steps into a directed graph structure.
    
    Rules:
    1. Summarize small consecutive walking steps into a single meaningful edge (e.g., "Walk 5 mins to Station").
    2. Keep Transit steps distinct.
    3. Ensure the graph is continuous (the 'node_to' of step A must be the 'node_from' of step B).
    4. Start the first node as "Start" and the last node as "Destination".
    5. Ensure step 'node_to' and 'node_from' have meaninful names instead of index numbers or letters, if the user is about to take a bus, indicate they are going from bus stop to bus stop.
    6. Ignore the time each step takes.
    7. Keep to a maximum of 5 words.
    """

    response = client.responses.parse(
        model="gpt-5-nano",
        instructions=system_prompt,
        input = maps_data,
        text_format=TreeStructure
    )

    content = response.output[1].content[0].text
    result = json.loads(content)
    
    if "edges" in result:
        return result["edges"]
    return result

def get_alternate_edges(data):
    route_context = json.dumps(data)
    
    system_prompt="""
        You are a Pessimistic Trip Planner. You receive a "Happy Path" (a correct route).
        For EVERY step in the Happy Path, generate 2 "Failure" alternatives (deviations).

        RULES:
        1. Input: A list of edges representing the correct journey.
        2. Output: A list of NEW edges representing what could go wrong at each starting point.
        3. The 'node_from' must match a node from the input.
        4. The 'node_to' must be a new, unique failure state (e.g., "Missed Bus", "Lost Wallet").
        5. If the step involves a Bus/Train, the failure must be transit-related (e.g., "Bus broke down").
        6. The "label" must give an explanation of how the failure state was reached (e.g. "trip and fall", "Missed Bus Stop"), avoid using the "node_to" as a "label".
        7. Keep labels short (max 5 words).
    """

    response = client.responses.parse(
        model="gpt-5-mini",
        instructions=system_prompt,
        input = [
            {"role": "user", "content": f"Generate failures for this route: {route_context}"}
        ],
        text_format=TreeStructure
    )

    content = response.output[1].content[0].text
    result = json.loads(content)

    if "edges" in result:
        return result["edges"]
    
    return result

def get_actions_for_failures(failure_nodes, tools):
    potential_actions = []
    for edge in failure_nodes:
        failure_node= edge.get("node_to")

        print(f"Failure node: {failure_node}")

        system_prompt="""
        Given an array of tools and a short situation affecting an elderly person's travel route, decide ALL relevant tool to solve solve the situation. 

        RULES:
        1. If no tool can solve the situaion, default to contacting the emergency contact.
        2. Do no return just the tool name, return a string of natural language (maximum 5 words) about the tool name (e.g. "ACTION: RECALCULATE ROUTE", "ACTION: CONTACT EMERGENCY CONTACT", "ACTION: EMAIL DOCTORS OFFICE")
        """

        response = client.responses.parse(
            model="gpt-5-mini",
            instructions=system_prompt,
            input = [
                {"role": "user", "content": f"Here is the situation to solve: {failure_node}.These are the tools: {tools}"}
            ],
            text_format=actions
        )    

        content = response.output[1].content[0].text
        result = json.loads(content)  

        potential_actions.append({"node": failure_node, "actions": result})  

    for action in potential_actions:
        print(action)
    

try:
    # gpt_edges = get_edges_from_gpt(data)

    # print(gpt_edges)
    gpt_original = [{'node_from': 'Start', 'node_to': 'Hendon Cemetery Bus Stop', 'label': 'Walk to Hendon Cemetery'}, {'node_from': 'Hendon Cemetery Bus Stop', 'node_to': 'Edgware Station Stop G', 'label': 'Bus 240 to Edgware'}, {'node_from': 'Edgware Station Stop G', 'node_to': 'Sheaveshill Avenue Stop CG', 'label': 'Bus 142 to Sheaveshill Ave'}, {'node_from': 'Sheaveshill Avenue Stop CG', 'node_to': 'Destination', 'label': 'Walk to Destination'}]

    gpt_edges = get_alternate_edges(gpt_original)

    print(gpt_edges)

    all_edges = gpt_original + gpt_edges

    tree = AutoTreePlotter(title="Failures route")

    for edge in all_edges:
        print(edge)
        tree_edge = tree.add_edge(edge.get("node_from"), edge.get("node_to"), edge.get("label"))
    
    tree.show()
    print("Graph generated successfully.")

except Exception as e:
    print(f"Error: {e}")


