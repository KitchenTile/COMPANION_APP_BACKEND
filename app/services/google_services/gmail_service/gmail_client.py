

from services.google_services.google_service_builder import GoogleServiceBuilder
from services.user_manager import CredentialManager


class GmailClient:
    def __init__(self, user_id: str):
        self.user_id = user_id

        # used to get user's tokens
        self.credential_manager = CredentialManager()

        # define scopes for service
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly",
                       "https://www.googleapis.com/auth/gmail.send", 
                       "https://www.googleapis.com/auth/gmail.modify"
                       ]
        
        # create service from GSB class
        self.service = GoogleServiceBuilder("gmail", "v1", self.credential_manager, self.user_id, self.scopes)


    def _get_service(self):
        return self.service.create_client()
    
    def get_emails(self):
        service = self._get_service()

        result = service.users().messages().list(
            userId="me",
            maxResults=10
        ).execute()

        print(result)

        return result.get("messages", [])