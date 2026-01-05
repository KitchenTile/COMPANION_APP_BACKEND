from services.google_services.google_service_builder import GoogleServiceBuilder
from services.user_manager import CredentialManager


class CalendarClient:
    def __init__(self, user_id: str):
        self.user_id = user_id
        # define credential manager for separation of concerns
        self.credential_manager = CredentialManager()

        # define scopes for service
        self.scopes = ["https://www.googleapis.com/auth/calendar.readonly",
                       "https://www.googleapis.com/auth/calendar.events", 
                       ]
        
        # create service from GSB class
        self.service = GoogleServiceBuilder("calendar", "v3", self.credential_manager, self.user_id, self.scopes)


    def _get_service(self):
        return self.service.create_client()
    
    def do_something(self):
        #create service
        service = self._get_service()

        return