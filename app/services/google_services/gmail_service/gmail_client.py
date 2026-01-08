

from services.google_services.google_service_builder import GoogleServiceBuilder
import base64

class GmailClient:
    def __init__(self, user_id: str, credential_manager):
        self.user_id = user_id

        # used to get user's tokens
        self.credential_manager = credential_manager

        # define scopes for service
        self.scopes = ["https://www.googleapis.com/auth/gmail.readonly",
                       "https://www.googleapis.com/auth/gmail.send", 
                       "https://www.googleapis.com/auth/gmail.modify"
                       ]
        
        # create service from GSB class
        self.service = GoogleServiceBuilder("gmail", "v1", self.credential_manager, self.user_id, self.scopes)


    def _get_service(self):
        return self.service.create_client()
    
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
    
    def get_emails(self):
        service = self._get_service()

        # get the last 10 emails
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
            
            emails = []
            for message in messages:
                single_email = service.users().messages().get(userId="me", id=message.get("id")).execute()

                # get email contents for the returned email object
                headers, body = self._format_email(single_email)

                single_email_obj = {
                    "id": message.get("id"),
                    "headers": headers,
                    "body": body.get("body"),
                }

                print("single email object")
                print(single_email_obj)

                emails.append(single_email_obj)

            return emails
        
        except Exception as e:
            print(e)