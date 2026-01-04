

import calendar
from datetime import datetime
import os
import time
from services.user_manager import CredentialManager
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

class GmailService:
    def __init__(self, user_id: str):
        self.user_id = user_id

        # used to get user's tokens
        self.credential_manager = CredentialManager()
        self.user_credentials = None

        self.client_id = os.environ.get("OAUTH_CLIENT2_ID")
        self.client_secret = os.environ.get("OAUTH_CLIENT2_SECRET")
        self.token_uri = "https://oauth2.googleapis.com/token"
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly",
                       "https://www.googleapis.com/auth/gmail.send", 
                       "https://www.googleapis.com/auth/gmail.modify"
                       ]


    def _build_credentials_object(self):
        token = self.credential_manager.get_google_tokens(self.user_id)

        self.user_credentials = Credentials(
            token = token['google_access_token'],
            refresh_token = token['google_refresh_token'],
            token_uri = self.token_uri,
            client_id = self.client_id,
            client_secret= self.client_secret,
            scopes= self.scopes,
        )
        
        self.user_credentials.expiry = datetime.fromisoformat(token['expiry'])

        print("succesfully built credentials object")


    def create_client(self):
        # if there's not a credentials objnect build it
        if not self.user_credentials:
            self._build_credentials_object()

        # if the token is expired refresh it and update the database
        if self.user_credentials.expired and self.user_credentials.refresh_token:
            self.user_credentials.refresh(Request())

            # epoch_time = calendar.timegm(time.strptime(self.user_credentials.expiry, '%Y-%m-%d %H:%M:%S.%f'))

            print(self.user_credentials.expiry)
            print("about to add new google tokens")
            self.credential_manager.add_google_tokens(self.user_id, self.user_credentials.token, self.user_credentials.refresh_token, self.user_credentials.expiry)
            print("google tokens added")

        
        print('building client')

        #build gmail service
        return build("gmail", "v1", credentials=self.user_credentials)