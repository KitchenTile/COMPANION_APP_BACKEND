import os
from supabase import Client, create_client
from datetime import datetime, timezone

class ConversationManager:
    def __init__(self, chat_id:str, user_id: str):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_API_KEY")

        self.user_id = user_id
        self.chat_id = chat_id

        self.client: Client = create_client(self.url, self.key)

        self.messages = self._load_message_history()

    # get user messages from database
    def _load_message_history(self):
        try:
            response = (
                self.client.table("chats").select("messages").eq("chat_id", self.chat_id).single().execute()
                )

            return response.data['messages'] if response.data else []
        except Exception:
            return []
        
    # add message to database
    def add_message(self, message: str, role: str):
        try:
            date = datetime.now(timezone.utc).isoformat()
            new_msg_obj = {"role": role, "content": message, "timestamp": date}

            #if we can't find the a chat with the provided id, create one.
            if not self._load_message_history():
                print(f"creting new chat: {self.chat_id}")

                # Define System Prompt
                system_msg = {
                    "role": "system",
                    "content": "You are an assistant. If you need more information, use 'user_interaction'.",
                    "timestamp": date
                }

                self.client.table("chats").insert({
                    "chat_id": self.chat_id,
                    "user_id": self.user_id,
                    "messages": [system_msg, new_msg_obj]
                }).execute()
            #else, add the message to the chat 
            else:
                self.client.rpc("add_chat_message", {
                    "p_chat_id": self.chat_id,
                    "p_new_message": new_msg_obj,
                }).execute();
            return None
        except Exception as e:
            print(f"Error adding message: {e}")