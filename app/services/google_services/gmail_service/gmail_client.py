from email.message import EmailMessage
from app.services.google_services.google_base_client import BaseGoogleClient
import base64

class GmailClient(BaseGoogleClient):
    def __init__(self, user_id: str, credential_manager, service, scopes):
        super().__init__(user_id = user_id, credential_manager = credential_manager, service = service, scopes = scopes)

    
    def watch_inbox(self):
        service = self._get_service()

        request_body = {
            'labelIds': ['INBOX'],
            'topicName': 'projects/trans-mind-481822-k1/topics/ai-companion-app'
        }
        
        try: 
            service.users().watch(userId="me", body=request_body).execute()
        except Exception as e:
            print(e)
        
    
    # helper function to extract header information
    def _get_header(self, headers, name):
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
            
        return None
    
    def _format_email(self, email):

        #get headers
        headers = email["payload"]["headers"]

        subject = self._get_header(headers, "Subject")
        sender = self._get_header(headers, "From")
        date = self._get_header(headers, "Date")
        message_id = self._get_header(headers, "Message-ID")
        thread_id = email['threadId']

        final_headers = {
            "subject": subject,
            "sender": sender,
            "date": date,
            'message_id': message_id,
            "thread_id": thread_id
        }

        #get body
        body_text = None

        for part in email["payload"].get("parts", []):

            if part["mimeType"] == "text/plain" and body_text is None:
                #decode body
                body_text = base64.urlsafe_b64decode(part["body"].get("data")).decode("utf-8")

        final_body = {
            "subject": subject,
            "body": body_text
        }


        return (final_headers, final_body)
    
    def get_email_ids(self):
        service = self._get_service()

        # get the last 10 email ids
        try:
            result = service.users().messages().list(
                    userId="me",
                    labelIds=["INBOX"],
                    maxResults=10
                ).execute()

            messages = result.get("messages", [])

            if not messages:
                print("No messages found.")
                return
            
            #get just the ids
            message_ids = []
            for message in messages:
                message_ids.append(message.get('id'))
            
            return message_ids
        except Exception as e:
            print(e)
    
    def get_emails(self, email_ids: list[str]):
        service = self._get_service()

        if len(email_ids) == 0:
            return None

        # from the email ids, get and format email objects
        try:
            emails = []
            for i in email_ids:
                single_email = service.users().messages().get(userId="me", id=i).execute()

                # get email contents for the returned email object
                headers, body = self._format_email(single_email)

                single_email_obj = {
                    "id": i,
                    "headers": headers,
                    "body": body.get("body"),
                }


                emails.append(single_email_obj)

            return emails
        
        except Exception as e:
            print(e)

    def create_email(
        self,
        to: str,
        subject: str,
        body: str,
        sender: str = "me"
    ):
        message = EmailMessage()
        message["To"] = to
        message["From"] = sender
        message["Subject"] = subject
        message.set_content(body)

        encoded_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        return {
            "raw": encoded_message,
        }

    def send_email(self, email_obj, thread_id: str ):
        service = self._get_service()

        body = email_obj.copy()

        if thread_id:
            body["threadId"] = thread_id

        return service.users().messages().send(
            userId="me",
            body=body
        ).execute()
