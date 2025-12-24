import json
from typing import Any, Dict, Optional
from uuid import uuid4
from app.services.agent_base import AgentBase
from app.services.orchestrator.memory import ConversationManager

class OrchestratorAgent(AgentBase):
    def __init__(self, name:str, client: Any, tool_definitions: list[Dict], tool_dict: Dict[str, callable], prompt: str, chat_id: str, user_id: str):
        super().__init__( name=name, client=client)

        self.tools = tool_definitions
        self.tool_dict = tool_dict
        self.prompt = prompt
        self.chat_id = chat_id
        self.user_id = user_id
        self.memory = ConversationManager(self.chat_id, self.user_id)
        self.task_id = None
        self.message_id = None

    #get message from redis broaker
    def receive_message(self, packet):
        print("message recieved...")
        #comes with task_id
        self.task_id = packet.get("task_id")

        #get message
        user_text = packet['content'].get("message")
            
        #if there's no tool usage
        if (packet.get("pending_tool_id") == None):
            # Log the user's start
            self.memory.add_process_log(self.task_id, "user", user_text)
        else:
            #get tool id
            tool_id = packet.get("pending_tool_id")

            #else add tool use to the process messages
            self.memory.add_process_log(
                task_id=self.task_id,
                step_type="tool_result",
                payload={
                    "tool_call_id": tool_id, 
                    "content": user_text
                }
            )
        
        # Start the Loop
        return self.run()

    #call LLM with parameters for differnet model (more or less thinking) and response format
    def _LLM_call(self, model):

        if not self.task_id:
            raise ValueError("No task_id set for LLM call")
        
        response = self.client.chat.completions.parse(
            model=model,
            messages=self.memory.compile_process_logs(self.task_id, self.prompt),
            tools=self.tools,
        )

        return response
    
    def _use_tool(self, tool_call):
        func_name = tool_call.function.name

        #if the tool is in the agent's tool box
        if func_name in self.tool_dict:
            try:
                print('---------- TOOL USE -----------')
                print(tool_call.function.name, tool_call.function.arguments)
                print('-------- END TOOL USE ---------')
                func_args = json.loads(tool_call.function.arguments)
                func = self.tool_dict[func_name]

                #use it
                result = func(**func_args)

                return result
            except Exception as e:
                return f"Error using tool: {e} raised"
        else:
            return f"Error: Tool {func_name} not found."

    
        #run loop
    def run(self):
        #orchestrator loop to avoid countless conditional statements
        while True:
            print(f"{self.name} starting loop...")
            #model call
            completion = self._LLM_call("gpt-5-nano")

            #get model to decide if they want to use tool
            completion.model_dump()

            #if we use tools, add the message to the message array 
            if completion.choices[0].message.tool_calls:

                #add the tool usage to the process log
                self.memory.add_process_log(
                    task_id=self.task_id,
                    step_type="assistant_tool_call", 
                    payload=completion.model_dump() 
                )

                #and loop to use tool(s)
                for tool_call in completion.choices[0].message.tool_calls:
                    result = self._use_tool(tool_call)

                    #check if the tool is a user question
                    if isinstance(result, dict) and result.get('action') == "ask_user":
                        print("in the user question conditional")
                        #send the question to the front end
                        self.memory.add_message(result['question'], "assistant")
                        #stop the function

                        user_reply = {
                            "performative": "REQUEST", 
                            "content": {"message": result['question']}, 
                            "task_id": self.task_id,
                            "pending_tool_id": tool_call.id ,
                            "message_id": self.message_id,
                            "user_id": self.user_id,
                            "chat_id": self.chat_id,
                            "sender": self.name,
                            "receiver": "USER"
                        } 
                        print(user_reply)

                        return user_reply

                    #log the tool use         
                    self.memory.add_process_log(
                        task_id=self.task_id,
                        step_type="tool_result",
                        payload={
                            "tool_call_id": tool_call.id, 
                            "content": str(result)
                        }
                    )
            else:
                # If no tools are called, return the models answer
                final_content = completion.choices[0].message.content

                print("final_content")
                print(final_content)
                
                self.memory.add_message(final_content, "assistant")
                
                return {
                    "performative": "INFORM",
                    "message_id": self.message_id,
                    "chat_id": self.chat_id,
                    "sender": self.name,
                    "receiver": "USER",

                    "user_id": self.user_id,
                    "task_id": self.task_id,

                    "content": {"message": self.user_message},
                }