from services.google_services.gmail_service.gmail_client import GmailClient
from services.user_manager import CredentialManager
from sentence_transformers import SentenceTransformer

class EmailChunker:
    def __init__(self, user_id: str, chunk_size: int = 500):

        self.user_id = user_id
        self.credential_manager = CredentialManager()
        self.chunk_size = chunk_size


    def chunk_emails(self):
        gmail_client = GmailClient(self.user_id, self.credential_manager)

        # array of email objects
        emails = gmail_client.get_emails()

        print("emails")

        print(emails)

        #chunk and add email bodies to array
        for email in emails:
            email_body = email.get("body")
            chunked_email_body = self._recursive_chunker(email_body)

            email["body"] = chunked_email_body
            print(len(chunked_email_body))

            print("new email")
            print(email)


        return emails

    def _recursive_chunker(self, text: str):
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
        if len(text) < self.chunk_size:
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
                recursively_chunked_pieces.extend(self._recursive_chunker(piece))
            
            #assemble into final chunks
            for piece in recursively_chunked_pieces:
                #check if adding the new piece overflows the chunk_size limit
                if len(current_chunk) + len(piece) + 1 > self.chunk_size:
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

        
        
class EmailEmbedder:
    def __init__(self):
        self.model = SentenceTransformer("Supabase/gte-small")

    def generate_embeddings(self, chunks: list[str]):
        return self.model.encode(
            chunks,
            normalize_embeddings=True
        ).tolist()

