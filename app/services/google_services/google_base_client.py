from abc import ABC, abstractmethod


class BaseGoogleClient(ABC):
    def __init__(self, user_id: str, credential_manager, service, scopes):
        self.user_id = user_id
        self.credential_manager = credential_manager
        self.service = service
        self.scopes = scopes

    def _get_service(self):
        return self.service.create_client()