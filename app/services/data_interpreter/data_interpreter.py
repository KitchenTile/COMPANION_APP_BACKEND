from datetime import datetime, timedelta
import json
import os
from typing import Literal

from pydantic import BaseModel, Field
from supabase import Client, create_client
from app.services.google_services.calendar_service.calendar_client import CalendarClient
from app.services.google_services.gmail_service.gmail_client import GmailClient
from app.services.data_interpreter.email_processor import EmailChunker, EmailEmbedder, EmailUpserter
from app.services.google_services.google_service_builder import GoogleServiceBuilder
from app.services.user_manager import CredentialManager

class AppointmentFilter(BaseModel):
    id: str | None
    summary: str | None= Field(
        description="A small sumary of the appointment information, maximum 15 words."
    )
    location: str | None = Field(
        description= "The address where the appointment is taking place at. This is just meant to be an address, NOT CLINIC OR HOSPITAL NAME",
        )
    date_time_start: str | None = Field(
        description= "The start date and time of the appointment.",
        json_schema_extra={
            "format": "date-time"
        }
        )
    date_time_end: str | None = Field(
        description= "The end date and time of the appointment.",
        json_schema_extra={
            "format": "date-time"
        }
        )
    intent: Literal["new", "cancel", "reschedule", None] = Field(
        description= "Wether the email is intended to create a new appointment, cancel an existing appointment, or reschedule an appointment's date."
        )

class AppoitmentFilterList(BaseModel):
    filtered_list: list[AppointmentFilter]


class EmailIngestionPipeline:
    def __init__(self, user_id, client):
        self.user_id = user_id

        #scopes
        scopes = [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send", 
            "https://www.googleapis.com/auth/gmail.modify",
        ]

        #services
        self.credential_manager = CredentialManager()

        gmail_service = GoogleServiceBuilder("gmail", "v1", self.credential_manager, user_id=self.user_id, scopes=scopes)

        self.gmail_service = GmailClient(self.user_id, credential_manager=self.credential_manager, service=gmail_service, scopes=scopes)
        self.client = client

        # email helpers
        self.email_chunker = EmailChunker(self.user_id)
        self.email_upserter = EmailUpserter(self.user_id)
        self.email_embedder = EmailEmbedder()

    
    def run(self):
        #get email_ids
        email_ids = self.gmail_service.get_email_ids()

        #filter the duplicated ids
        duplicate_email_ids = self.email_upserter.filter_email_ids(email_ids)

        print("duplicate email ids")
        print(duplicate_email_ids)

        
        if not duplicate_email_ids:
            new_email_ids = email_ids
        else:
            #get emails that are not inclided in our duplicated ids
            new_email_ids = [id for id in email_ids if id not in duplicate_email_ids]

        if not new_email_ids:
            print("No new emails to upload")
            return
        
        new_emails = self.gmail_service.get_emails(new_email_ids)

        # filter emails to see if they're appointments
        appointment_emails = self.filter_appointments(new_emails)

        if not appointment_emails:
            print("No new appointments to upload")
            return

        # chunk appointment emails
        chunked_emails = self.email_chunker.chunk_emails(appointment_emails)

        #process each email
        for email in chunked_emails:
            try:
                self.process_email(email)
            except Exception as e:
                print(f"Failed to process email {email.get('id')}: {e}")
        
        return appointment_emails


    def process_email(self, email):
        #email's chunks
        chunks = email.get("body")

        #generate embeddings and add to email object
        embeddings = self.email_embedder.generate_embeddings(chunks)

        #upsert email's metadata
        self.email_upserter.upsert_email(email)

        #upsert chunks + embeddings
        for index, chunk in enumerate(chunks):
            self.email_upserter.upsert_chunk(chunk, index, email.get("id"), embeddings[index])
            print(f"successfully addded email embeddings for email: {email.get('id')}")
    

    # given an array of emails get appointent info and intent
    def filter_appointments(self, emails):
        prompt = f"""
        Analyze these email and only filter emails that are DEFINITELY medical appointment related.
        If emails have the same thread_id, they are related. If a later emails is of intent = "reschedule", use previous email to fill up information as you see fit while returning schemas for both emails.
        Ignore and do not return a json schema for generic newsletters or other emails. 
            
        Emails:
        {json.dumps(emails)}
        """

        #gpt call
        response = self.client.responses.parse(
            model="gpt-5-mini",
            input=prompt,
            text_format=AppoitmentFilterList,
        )

        response_model = response.output[1].content[0].parsed

        #if the list is empty there are no appoitnment emails
        if not response_model.filtered_list:
            return None

        response_dump = response_model.model_dump()

        print(response_dump)

        appointment_emails = []
        # add appointment details to the emails about appointments and pop the ones that are not
        for email in emails:
            for response in response_dump.get("filtered_list"):
                if email.get("id") == response.get("id"):
                    email["appointment_details"] = response
                    print(email)
                    appointment_emails.append(email)
                    break

        print("final emails with appointment info")
        print(appointment_emails)

        return appointment_emails
    

class CalendarEventManager:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.credential_manager = CredentialManager()

        #scopes
        scopes = [
            "https://www.googleapis.com/auth/calendar.readonly",
            "https://www.googleapis.com/auth/calendar.events",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send", 
            "https://www.googleapis.com/auth/gmail.modify",
        ]

        calendar_service = GoogleServiceBuilder("calendar", "v3", self.credential_manager, user_id=self.user_id, scopes=scopes)


        self.google_calendar_client = CalendarClient(self.user_id, self.credential_manager, service=calendar_service, scopes=scopes)
        
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_API_KEY")
        
        self.client: Client = create_client(self.url, self.key)
        
    #go through appointment list and decide what to do based on intent
    def manage_calendar_events(self, appointments):
        print("in manage calendar")
        print(appointments)
        for appointment in appointments:
            appointment_thread_id = appointment.get("headers").get("thread_id")
            appointment_start_time = appointment.get("appointment_details").get("date_time_start")
            appointment_summary = appointment.get("appointment_details").get("summary")
            appointment_end_time = appointment.get("appointment_details").get("date_time_end")

            # if no end time make one 1hr after the event's beggining
            if not appointment_end_time:
                appointment_end_time = generate_end_time(appointment_start_time=appointment_start_time, time_added=1)

            if appointment.get("appointment_details").get("intent") == "new":
                self._create_new_appointment_event(appointment_summary=appointment_summary, appointment_end_time=appointment_end_time, appointment_start_time=appointment_start_time, appointment_thread_id=appointment_thread_id)
                    
            if appointment.get("appointment_details").get("intent") == "reschedule":
                self._reschedule_appointment(appointment_summary=appointment_summary, appointment_end_time=appointment_end_time, appointment_start_time=appointment_start_time, appointment_thread_id=appointment_thread_id)

            if appointment.get("appointment_details").get("intent") == "cancel":
                self._cancel_appointment(appointment_thread_id)


    def _create_new_appointment_event(self, appointment_start_time, appointment_end_time, appointment_summary, appointment_thread_id):
        print("NEW APPOINTMENT")

        # check for conflicting events with get_all_events
        is_free = self.google_calendar_client.check_freebusy(appointment_start_time, appointment_end_time)

        if is_free:
            # create new event
            event_obj = {
                "summary": appointment_summary,
                "start": {"dateTime": appointment_start_time},
                "end": {"dateTime": appointment_end_time},
                "extendedProperties": {
                    "private": {
                        "thread_id": appointment_thread_id
                    }
                }                        
            }
            try:
                self.google_calendar_client.add_event(event_obj)
                print("CREATED NEW APPOINTMENT")
            except Exception as e:
                print(e)

        else:
            print("CONFLICTING EVENTS FOUND")

    def _reschedule_appointment(self, appointment_summary, appointment_start_time, appointment_end_time, appointment_thread_id):
        #get event id with get_event_by_thread_id(thread_id) and edit it with edit_event(event_id, edit_obj)
        print("RESCHEDULE APPOINTMENT")

        event_id_to_edit = self.google_calendar_client.get_event_by_thread_id(appointment_thread_id)

        event_obj = {
            "summary": appointment_summary,
            "start": {"dateTime": appointment_start_time},
            "end": {"dateTime": appointment_end_time},
            "extendedProperties": {
                "private": {
                    "thread_id": appointment_thread_id
                }
            }                         
        }
        self.google_calendar_client.edit_event(event_id_to_edit, event_obj)


    def _cancel_appointment(self, appointment_thread_id: str):
        print("CANCEL APPOINTMENT")
        # get event id with get_event_by_thread_id(event_id) and cancel it with cancel_event(event_id)
        event_id_to_cancel = self.google_calendar_client.get_event_by_thread_id(appointment_thread_id)

        print(event_id_to_cancel)
        self.google_calendar_client.delete_event(event_id_to_cancel)


def generate_end_time(appointment_start_time, time_added):

    start_time = datetime.fromisoformat(appointment_start_time.replace("Z", "+00:00"))
    end_time = start_time + timedelta(hours=time_added)

    end_str = end_time.isoformat().replace("+00:00", "Z")

    return end_str