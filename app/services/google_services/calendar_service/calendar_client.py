from services.google_services.google_service_builder import GoogleServiceBuilder
from services.user_manager import CredentialManager
from datetime import datetime, timezone


class CalendarClient:
    def __init__(self, user_id: str):
        self.user_id = user_id
        # define credential manager for separation of concerns
        self.credential_manager = CredentialManager()

        # define scopes for service
        self.scopes = ["https://www.googleapis.com/auth/calendar.readonly",
                       "https://www.googleapis.com/auth/calendar.events", 
                       ]
        
        # create service from GSB class
        self.service = GoogleServiceBuilder("calendar", "v3", self.credential_manager, self.user_id, self.scopes)


    def _get_service(self):
        return self.service.create_client()
    
    def add_event(self, event_obj):
        #create service
        service = self._get_service()

        # create event
        try: 
            event = service.events().insert(
                calendarId="primary",
                body=event_obj
            ).execute()

            print(event)

        except Exception as e:
            print(e)

        # return event
    
    #gets all future events
    def get_all_events(self):
        #create service
        service = self._get_service()

        # create event
        try: 
            events = service.events().list(
                calendarId="primary",
                singleEvents=True,
                orderBy="startTime",
                timeMin= datetime.now(timezone.utc).isoformat()
            ).execute()

            print(events)

            return events.get("items", [])

        except Exception as e:
            print(e)

        # return event

    def get_single_event(self, event_id: str):
        #create service
        service = self._get_service()

        # get event from event id
        try:
            event = service.events().get(
                calendarId="primary",
                eventId=event_id
            ).execute()

            print(f"event {event_id}: {event}")

            #change return statement to get the item from the event
            return event
        except Exception as e:
            print(e)

    def edit_event(self, event_id: str, edit_obj):
        #create service
        service = self._get_service()

        #edit event based on event id
        try:
            edited_event = service.events().patch(
                calendarId="primary",
                eventId=event_id,
                body=edit_obj
            ).execute()

            print(edited_event)

            return edited_event

        except Exception as e:
            print(e)
        
    def delete_event(self, event_id: str):
        #create service
        service = self._get_service()

        #delete event based on event id
        try:
            service.events().delete(
                calendarId="primary",
                eventId=event_id
            ).execute()

            print(f"event {event_id} deleted")
        except Exception as e:
            print(f"failed to delete event {event_id}: {e}")
        