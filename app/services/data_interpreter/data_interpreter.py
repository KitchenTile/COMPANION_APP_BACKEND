from app.services.google_services.gmail_service.gmail_client import GmailClient
from services.data_interpreter.email_processor import EmailChunker, EmailEmbedder, EmailUpserter
from services.user_manager import CredentialManager


class EmailProcessingPipeline:
    def __init__(self, user_id):
        self.user_id = user_id

        #services
        self.credential_manager = CredentialManager()
        self.gmail_service = GmailClient(self.user_id, credential_manager=self.credential_manager)

        # email helpers
        self.email_chunker = EmailChunker(self.user_id)
        self.email_upserter = EmailUpserter(self.user_id)
        self.email_embedder = EmailEmbedder()

    
    def run(self):
        #get email_ids
        
        #get emails 
        email_ids = self.gmail_service.get_email_ids()

        #filter the duplicated ids
        duplicate_email_ids = self.email_upserter.filter_emails(email_ids)

        #get emails that are not inclided in our duplicated ids
        new_email_ids = [id for id in email_ids if id not in duplicate_email_ids]

        if not new_email_ids:
            print("No new emails to upload")
            return
        
        new_emails = self.gmail_service.get_emails(new_email_ids)
        
        # chunk new emails
        chunked_emails = self.email_chunker.chunk_emails(new_emails)

        #process each email
        for email in chunked_emails:
            try:
                self.process_email(email)
            except Exception as e:
                print(f"Failed to process email {email.get('id')}: {e}")

        pass

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

 