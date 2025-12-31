import os
from typing import Optional
from supabase import Client, create_client
from datetime import datetime, timezone

class CredentialManager:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_API_KEY")

        self.client: Client = create_client(self.url, self.key)

    def add_google_tokens(self, user_id, access_token, refresh_token):
        try:
            # if there's a user id, then add a credentials row for it
            response = self.client.table("user_credentials").upsert({
                "user_id": user_id,
                "google_access_token": access_token,
                "google_refresh_token": refresh_token,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()

            print("Successfully saved tokens")
            return response
        
        except Exception as e:
            return f"error adding user token to database: {e}"
        
    def get_google_tokens(self, user_id):
        try:
            # if there's a user id, then add a credentials row for it
            response = self.client.table("user_credentials").select("google_access_token, google_refresh_token").eq("user_id", user_id).single().execute()
            print("retrieved tokens")
            print(response.data)
            return response.data
        
        except Exception as e:
            return f"error adding user token to database: {e}"



    
    