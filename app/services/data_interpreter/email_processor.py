from app.services.google_services.gmail_service.gmail_client import GmailClient
from app.services.user_manager import CredentialManager


class EmailEmbeddingProcessor:
    def __init__(self, user_id: str):

        self.user_id = user_id
        self.credential_manager = CredentialManager()


    def _chunk_emails(self):
        gmail_client = GmailClient(self.user_id, self.credential_manager)

        # array of email objects
        emails = gmail_client.get_emails()

        chunked_email_bodies = []
        #chunk and add email bodies to array
        for email in emails:
            email_body = email.get("body")
            chunked_email_body = self._recursive_chunker(email_body, 500)
            
            chunked_email_bodies.append(chunked_email_body)

        print(chunked_email_bodies)

        return chunked_email_bodies

    def _recursive_chunker(self, text: str, chunk_size: int = 500):
        text_separators = [
            "\n\n",
            "\n",
            " ",
            ".",
            ",",
            "\u200b",
            "\uff0c",
            "\u3001",
            "\uff0e",
            "\u3002",
        ]

        combined_chunks = []
        current_chunk = ""

        # if the text is short enogh return it as a chunk
        if len(text) < chunk_size:
            combined_chunks.append(text)
            return combined_chunks
        else:
            text_pieces = [text]

            #find the largest separator and split the text
            for separator in text_separators:
                if text.find(separator) != -1:
                    text_pieces = text.split(separator)
                    break
            
            #recursively split all text pieces to make sure they are all under the chunk_size
            recursively_chunked_pieces = []
            for piece in text_pieces:
                recursively_chunked_pieces.extend(self._recursive_chunker(piece, chunk_size))
            
            #assemble into final chunks
            for piece in recursively_chunked_pieces:
                #check if adding the new piece overflows the chunk_size limit
                if len(current_chunk) + len(piece) + 1 > chunk_size:
                    if current_chunk:
                        combined_chunks.append(current_chunk)
                    current_chunk = piece
                else:
                    if current_chunk:
                        current_chunk += " " + piece
                    else:
                        current_chunk = piece

            
            if current_chunk:
                combined_chunks.append(current_chunk)

            return combined_chunks

        
        
        