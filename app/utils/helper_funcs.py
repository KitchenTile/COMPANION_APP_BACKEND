from app.services.google_services.calendar_service.calendar_client import CalendarClient
from app.services.google_services.gmail_service.gmail_client import GmailClient
from app.services.google_services.google_service_builder import GoogleServiceBuilder


def trigger_gmail_watch_service(credential_manager, user_id):
    print(f"Background Task: Setting up Gmail watch for {user_id}")

    scopes = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send", 
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    gmail_service = GoogleServiceBuilder("gmail", "v1", credential_manager, user_id=user_id, scopes=scopes)

    gmail_client = GmailClient(user_id=user_id, credential_manager=credential_manager, scopes=scopes, service=gmail_service)

    gmail_client.watch_inbox()

