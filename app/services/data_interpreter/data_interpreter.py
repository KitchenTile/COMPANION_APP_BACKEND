import json
from typing import Literal

from pydantic import BaseModel, Field
from services.google_services.gmail_service.gmail_client import GmailClient
from services.data_interpreter.email_processor import EmailChunker, EmailEmbedder, EmailUpserter
from services.user_manager import CredentialManager

class AppointmentFilter(BaseModel):
    id: str | None
    summary: str | None= Field(
        description="A small sumary of the email, maximum 15 words."
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

        #services
        self.credential_manager = CredentialManager()
        self.gmail_service = GmailClient(self.user_id, credential_manager=self.credential_manager)
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
    

    def filter_appointments(self, emails):
        prompt = f"""
        Analyze these emails and only filter emails that are DEFINITELY medical appointment related.
        Ignore and do not return a json schema for generic newsletters or other emails. 
            
        Emails:
        {json.dumps(emails)}
        """

        #gpt call
        response = self.client.responses.parse(
            model="gpt-5-mini",
            input=prompt,
            text_format=AppointmentFilter,
        )

        response_model = response.output[1].content[0].parsed

        #if the list is empty there are no appoitnment emails
        if len(response_model) == 0:
            return None

        response_dump = response_model.model_dump()

        print(response_dump)

        # add appointment details to the emails about appointments and pop the ones that are not
        for index, email in enumerate(emails):
            for response in response_dump.get("filtered_list"):
                if email.get("id") == response.get("id"):
                    email["appointment_details"] = response
                    print(email)
                    break

            if not email.get("appointment_details"):
                print(f"email {email.get("id")}, indexed {index}, is not about appointments")
                emails.pop(index)

        print(emails)

        return emails
