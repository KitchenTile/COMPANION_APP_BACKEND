import os
import uuid
from pydantic import BaseModel
from realtime import Any
from supabase import Client, create_client
from services.google_services.gmail_service.gmail_client import GmailClient
from sentence_transformers import SentenceTransformer

# class email(BaseModel):
#     id: str
#     headers: dict[str, Any]
#     body: str

class EmailChunker:
    def __init__(self, user_id: str, chunk_size: int = 500):
        self.user_id = user_id
        self.chunk_size = chunk_size


    def chunk_emails(self, emails):

        #chunk and add email bodies to array
        for email in emails:
            email_body = email.get("body")
            chunked_email_body = self._recursive_chunker(email_body)

            email["body"] = chunked_email_body
            # print(len(chunked_email_body))
            # print("new email")
            # print(email)

        return emails

    def _recursive_chunker(self, text: str):

        if not text:
            return []

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

class EmailUpserter:
    def __init__(self, user_id):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_API_KEY")
        
        self.client: Client = create_client(self.url, self.key)

        self.user_id = user_id

    # upload email metadata
    def upsert_email(self, email):
        try:
            headers = email.get("headers")
            response = self.client.table("emails").upsert({
                "id": email.get("id"),
                "user_id": self.user_id,
                "subject": headers.get("subject"),
                "sender": headers.get("sender"),
                "date": headers.get("date"),
                "gmail_message_id": headers.get("message_id"),
                "thread_id": headers.get("thread_id"),
            }).execute()

            return response

        except Exception as e:
            print(e)

    #upload chunk data
    def upsert_chunk(self, chunk, chunk_index, email_id, embedding):
        try:
            response = self.client.table("email_chunks").upsert({
                "id": str(uuid.uuid4()),
                "user_id": self.user_id,
                "email_id": email_id,
                "chunk_content": chunk,
                "embedding": embedding,
                "chunk_order": chunk_index
            },
            on_conflict="email_id, chunk_order"
            ).execute()

            return response
        except Exception as e:
            print(e)

    def filter_email_ids(self, email_ids):
        if not email_ids:
            return set()
        try:
            response = self.client.table("emails").select('id').in_("id", email_ids).execute()

            print(response)
            
            return {row['id'] for row in response.data}
        
        except Exception as e:
            print(f"Error checking existing IDs: {e}")
            return set()