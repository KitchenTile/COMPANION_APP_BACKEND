import os
from supabase import Client, create_client

class ConversationManager:
    def __init__(self, chat_id:str, user_id: str):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_API_KEY")

        self.user_id = user_id
        self.chat_id = chat_id

        self.client: Client = create_client(self.url, self.key)

        self.messages = self._load_message_history()

    def _load_message_history(self):
        try:
            response = (
                self.client.table("chats").select("messages").eq("user_id", self.user_id).single().execute()
                )

            return response.data['messages'] if response.data else []
        except Exception as e:
            print(f"Error initializing chat: {e}")

    def add_message(self, message: str):
        try:
            return
        except Exception as e:
            print(f"Error adding message: {e}")