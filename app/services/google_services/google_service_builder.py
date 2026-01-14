from datetime import datetime
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

class GoogleServiceBuilder():
    def __init__(self, service_name: str, service_version: str, credential_manager, user_id: str, scopes: list[str]):
        self.user_id = user_id
        self.scopes = scopes
        self.service_name = service_name
        self.service_version = service_version

        # for credentials obj
        self.client_id = os.environ.get("OAUTH_CLIENT2_ID")
        self.client_secret = os.environ.get("OAUTH_CLIENT2_SECRET")
        self.token_uri = "https://oauth2.googleapis.com/token"

        #used to get usre's token to build credentials object
        self.credential_manager = credential_manager
        self.user_credentials = None



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
            self.credential_manager.add_google_tokens(self.user_id, self.user_credentials.token, self.user_credentials.refresh_token, self.user_credentials.expiry)

        print('building client')

        #build gmail service
        return build(self.service_name, self.service_version, credentials=self.user_credentials)