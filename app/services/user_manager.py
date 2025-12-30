import os
from typing import Optional
from supabase import Client, create_client
from datetime import datetime, timezone

class UserManager:
    def __init__(self, user_id: Optional[str] = None):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_API_KEY")

        self.client: Client = create_client(self.url, self.key)
        self.user_id = None

    # create user
    def create_user(self, email: str, password: str):
        try:
            print("here")
            response = (
                self.client.auth.sign_up(
                        {
                            "email": email,
                            "password": password,
                        }
                    )
                )
            print("create user response")
            print(response)

            return response
        except Exception as e:
            return f"error creating user: {e}"
        
    # user login
    def user_login(self, email: str, password: str):
        try:
            response = (
                self.client.auth.sign_in_with_password(
                        {
                            "email": email,
                            "password": password,
                        }
                    )
                )
            print("log in response")
            print(response)

            print('user id')
            print(response.user.id)
            

            return response
        except Exception as e:
            return f"error loggin user in: {e}"
        
    # add message to database
    def user_log_out(self):
        try:
            response = response = self.client.auth.sign_out()
            print("sign out response")
            print(response)
            
            return response
        except Exception as e:
            return f"error signing user out: {e}"
    
    