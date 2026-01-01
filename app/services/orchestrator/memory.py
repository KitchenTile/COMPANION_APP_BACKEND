import os
from supabase import Client, create_client
from datetime import datetime, timezone
from uuid import uuid4

class ConversationManager:
    def __init__(self, chat_id:str, user_id: str):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_API_KEY")

        self.user_id = user_id
        self.chat_id = chat_id

        self.client: Client = create_client(self.url, self.key)

        self.messages = self._load_message_history()

    # get conversation messages from database
    def _load_message_history(self):
        try:
            response = (
                self.client.table("chats").select("messages").eq("chat_id", self.chat_id).single().execute()
                )

            return response.data['messages'] if response.data else []
        except Exception:
            return []
        
    # add message to database
    def add_message(self, message: str, role: str) -> None:
        try:
            date = datetime.now(timezone.utc).isoformat()
            new_msg_obj = {"role": role, "content": message, "timestamp": date}

            #if we can't find the a chat with the provided id, create one.
            if not self._load_message_history():
                print(f"creting new chat: {self.chat_id}")

                #insert first message
                self.client.table("chats").insert({
                    "chat_id": self.chat_id,
                    "user_id": self.user_id,
                    "messages": new_msg_obj
                }).execute()
            #else, add the message to the chat 
            else:
                self.client.rpc("add_chat_message", {
                    "p_chat_id": self.chat_id,
                    "p_new_message": new_msg_obj,
                }).execute();
        except Exception as e:
            print(f"Error adding message: {e}")
    
    #process_log is a table database that acts as the internal memory for the reasoning model
    #add process step into process database
    def add_process_log(self, task_id: str, step_type: str, payload: dict):
        try:
            self.client.table("process_log").insert({
                "task_id": task_id,
                "chat_id": self.chat_id,
                "step_type": step_type,
                "payload": payload
            }).execute()
        except Exception as e:
            print(f"Error adding process log: {e}")

    #get the process logs in order so the reasoning model to keep context
    def get_process_log(self, task_id: str):
        try:
            response = self.client.table("process_log").select("*").eq("task_id", task_id).order("created_at", desc=False).execute()
            return response.data if response.data else []
        except Exception as e:
            print(f"Error getting process log: {e}")
    
    # compile process log into messages expeced from model
    def compile_process_logs(self, task_id: str, system_prompt_text: str):
        # This is system prompt first
        messages = [
            {"role": "system", "content": system_prompt_text}
        ]

        #  Get history from DB
        history_rows = self.get_process_log(task_id)

        # reconstruct exact format needed
        for row in history_rows:
            step_type = row['step_type']
            payload = row['payload']

            if step_type == 'user':
                messages.append({"role": "user", "content": payload})

            elif step_type == 'thought':
                messages.append({"role": "assistant", "content": payload})

            elif step_type == 'assistant_tool_call':
                message_data = payload['choices'][0]['message']
                messages.append(message_data)

            elif step_type == 'tool_result':
                messages.append({
                    "role": "tool",
                    "tool_call_id": payload.get("tool_call_id"),
                    "content": payload.get("content")
                })

        return messages

    # add coords where user's get lost at to the DB
    def add_lost_coords(self, lost_coords, destination, user_id):
        # check if DB has an entry from user
        response = (
            self.client.table("user_derail_coords")
            .select("*").eq("user_id", user_id)
            .execute()
        )

        # if there is a row for the user
        if response.data != []:
            print(response)
            try:
                new_coords_obj = {
                        "lost_coords": lost_coords,
                        "id": str(uuid4()),
                        "lost_coords": lost_coords,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "destination": destination
                    }
                # we add a new entry in the coords column

                self.client.rpc("add_lost_coord", {
                    "p_user_id": user_id,
                    "p_new_coord": new_coords_obj,
                }).execute();

            except Exception as e:
                print(f"Error adding coords to table: {e}")
        else:
            # if there's no record, create one with the first coords as the starting array
            try:
                self.client.table("user_derail_coords").insert({
                "id": str(uuid4()),
                    "user_id": user_id,
                    "lost_coords": [{
                        "id": str(uuid4()),
                        "lost_coords": lost_coords,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "destination": destination
                    }]
                }).execute()
            except Exception as e:
                print(f"Error adding coords to table: {e}")