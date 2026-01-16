from app.services.google_services.google_base_client import BaseGoogleClient
from datetime import datetime, timezone


class CalendarClient(BaseGoogleClient):
    def __init__(self, user_id: str, credential_manager, service, scopes: list[str]):
        super().__init__(user_id = user_id, credential_manager = credential_manager, service = service, scopes = scopes)
  
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

    def check_freebusy(self, time_min, time_max):
        service = self._get_service()

        body = {
            "timeMin": time_min,
            "timeMax": time_max,
            "items": [
                {"id": "primary"}
            ]
        }

        try:
            event_freebusy = service.freebusy().query(body=body).execute()

            print(event_freebusy)

            if len(event_freebusy['calendars']['primary']['busy']) == 0:
                return True
            else:
                return False
            
        except Exception as e:
            print(" --- event freebusy error --- ")
            print(e)


    def get_event_by_thread_id(self, thread_id: str):
        #create service
        service = self._get_service()
        print("get_event_by_thread_id")
        # get event from event id
        try:
            events = (
                service.events()
                .list(
                    calendarId="primary",
                    privateExtendedProperty=f"thread_id={thread_id}"
                )
                .execute()
            )

            print(events)
            #change return statement to get the item from the event
            return events.get("items")[0].get("id")
        
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
        