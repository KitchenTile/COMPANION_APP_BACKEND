import base64
from http import client
import json
import os

from openai import OpenAI
from supabase import create_client
from app.services.data_interpreter.data_interpreter import CalendarEventManager, EmailIngestionPipeline
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


def execute_gmail_task(data):
    client = OpenAI()

    # decode data
    data_decoded = base64.b64decode(data).decode("utf-8")
    # get email from data
    email = json.loads(data_decoded).get("emailAddress")

    print(email)
    
    supabase = create_client(
        os.environ.get("SUPABASE_URL"),
        os.environ.get("SUPABASE_API_KEY")
    )
    
    # get user_id from supabase 
    try:
        response = supabase.table("users").select('id').eq("email", email).single().execute()
    except Exception as e:
        print(e)

    user_id = response.data["id"]

    print("initializing email and calendar classes")

    # initialize classes for data processing
    email_processor = EmailIngestionPipeline(user_id, client)
    calendar_processor = CalendarEventManager(user_id)

    #process data
    appointments = email_processor.run()

    print("appointments")
    print(appointments)

    if appointments:
        calendar_processor.manage_calendar_events(appointments)


