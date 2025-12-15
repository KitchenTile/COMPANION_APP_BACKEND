import json
from typing import Any, Dict, Optional
from app.services.agent_base import AgentBase
from app.services.orchestrator.memory import ConversationManager


class OrchestratorAgent(AgentBase):
    def __init__(self,name:str, client: Any ,tool_definitions: list[Dict], tool_dict: Dict[str, callable], prompt: str, chat_id: str, user_id: str):
        super().__init__( name, client)

        self.tools = tool_definitions
        self.tool_dict = tool_dict
        self.prompt = prompt
        self.chat_id = chat_id
        self.user_id = user_id
        self.memory = ConversationManager(self.chat_id, self.user_id)
        self.task_id = None

    #get message from redis broaker
    def receive_message(self, packet: Dict[str, Any]):
        #comes with task_id
        self.task_id = packet.get("task_id")
        #and message
        user_text = packet['content'].get("text")
        
        # Log the user's start
        self.memory.add_process_log(self.task_id, "user", user_text)
        
        # Start the Loop
        return self.run()

    #call LLM with parameters for differnet model (more or less thinking) and response format
    def _LLM_call(self, model, response_format: Optional[Dict] = None):

        if not self.task_id:
            raise ValueError("No task_id set for LLM call")
        
        response = self.client.chat.completions.parse(
            model=model,
            messages=self.memory.compile_process_logs(self.task_id, self.prompt),
            tools=self.tools,
            response_format=response_format
        )

        return response
    
    def _use_tool(self, tool_call):

        #if the tool is in the agent's tool box
        if func_name in self.tool_dict:
            try:
                print(tool_call.function.name, tool_call.function.arguments)
                func_name = tool_call.function.name
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
                        return {
                            "status": "needs_info", 
                            "data": result['question'], 
                            "task_id": self.task_id,
                            "pending_tool_id": tool_call.id 
                        } 

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
                
                self.memory.add_message(final_content, "assistant")
                
                return {
                    "status": "completed",
                    "data": final_content,
                    "task_id": self.task_id
                }
