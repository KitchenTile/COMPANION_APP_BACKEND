from app.services.google_services.gmail_service.gmail_client import GmailClient
from app.services.user_manager import CredentialManager


class DataScraper:
    def __init__(self, user_id: str):

        self.user_id = user_id

        self.credential_manager = CredentialManager()


    def chunk_emails(self):
        gmail_client = GmailClient(self.user_id, self.credential_manager)

        # emails = 

        
        