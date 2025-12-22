
import uuid
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import requests
import os

#load env file
load_dotenv()

client = OpenAI()



#tool def
def calculate_google_maps_route(origin: str, destination: str, transport_mode: list[str]):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": os.getenv("GOOGLE_MAPS_API_KEY"),
        "X-Goog-FieldMask": "routes.*"
    }

    try:
        data = {
            "origin": {
                "address": origin
                },
            "destination": {
                "address": destination
                },
            "travelMode": "TRANSIT",
            "computeAlternativeRoutes": False,
            "transitPreferences": {
                "routingPreference": "LESS_WALKING",
                "allowedTravelModes": transport_mode
            }
        }

        response = requests.post('https://routes.googleapis.com/directions/v2:computeRoutes', headers=headers, json=data)    

        data = response.json()
        
        route = data['routes'][0]

        #get fastest route metadata
        route_summary = {
            # "route_id": index + 1,
            "duration": route.get("localizedValues", {}).get("duration", {}).get("text"),
            "distance": route.get("localizedValues", {}).get("distance", {}).get("text"),
            "fare": route.get("localizedValues", {}).get("transitFare", {}).get("text", "N/A"),
            "steps": []
        }

        # go through the route steps and add them to the summary
        for leg in route.get("legs", []):
            for index, step in enumerate(leg.get("steps", [])):

                # Handle Transit Details
                if "transitDetails" in step:
                    transit = step["transitDetails"]
                    line = transit.get("transitLine", {})

                    step_instruction = (
                        f"Step {index + 1}: "
                        f"Take {line.get('vehicle', {}).get('name', {}).get('text')} "
                        f"{line.get('nameShort', line.get('name'))} "
                        f"towards {transit.get('headsign')} "
                        f"for {transit.get("stopCount")} stops ({step.get("localizedValues", {}).get("staticDuration", {}).get("text")}), "
                        f"from {transit.get("stopDetails", {}).get("departureStop", {}).get("name")} "
                        f"until {transit.get("stopDetails", {}).get("arrivalStop", {}).get("name")}."
                    )
                    

                # Handle Walking Details
                elif "navigationInstruction" in step:
                    nav = step["navigationInstruction"]

                    step_instruction = (
                        f"Step {index + 1}: {nav.get("instructions", "Walk")}. "
                        f"It should take {step.get("localizedValues", {}).get("staticDuration", {}).get("text")} ({step.get("localizedValues", {}).get("distance", {}).get("text")})"
                    )
                
                route_summary["steps"].append(step_instruction)
        

        return route_summary

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"


calculate_google_maps_route("91C Church Road, NW4 4DP, London", "42 Grosvenor Terrace, SE5 0NP, London", ["BUS", "SUBWAY"])



txt = '1 hour 16 mins'
txt_2 = '1 hour 17 mins'
txt_3 = '1 hour 14 mins'
txt_4 = '1 hour 20 mins'

times = [txt,txt_2,txt_3,txt_4]
times_mins = {}

for index, time in enumerate(times):
	x = time.split()
	if len(x) > 2:
		hr = x[0]
		mins = x[2]
		mins_total = int(hr) * 60 + int(mins)
		times_mins[index] = mins_total
	else:
		times_mins[index] = x[0]
        

sorted_times = dict(sorted(times_mins.items(), key=lambda item: item[1]))

print(next(iter(sorted_times)))

from math import sin, cos, sqrt, atan2, radians

polyline = 'ozyyHfek@BFdCiDtDeGvB}DlDmHxCmHrAoDhCeIjIkXxPsf@h@cBb@sBb@_DTuCDuCEcDOsC_A{IMgCCsCDsCNuB\\sC`@uBlCsJh@oCZ{BhBgRj@oFbAeI`@mBTw@l@_BbAiBzAkBp@o@fBkArAi@dBc@xCSvBEvIAvCInD[zA]`Bg@bBaA~CqBbCgBpD_DjHaHhGaH`FeHzDgHzCeH`CeHnBaH|A{GhD_PrAaGzAsFhBeFpB{EzBoEbCkEvKwQdCkE`CuExB_FpBgFhBsFbBuFnGqUrA{EbB_FtCoHhAa@hAk@jD}B|I}HpGcGfKoLxQ}Rz@_A^Or@Ev@P\\X^l@x@bChDbLn@rBp@~B^v@\\`@dAl@|@Rz@BdAQdBw@`CwAdBoAlFyEvJcJjMwM`FyEv@m@d@S`Dk@|DeAbEoA|FeCfBy@t@KzC?pAAfASx@c@PQj@iAnF{MjFsLX{@ZeBfFm]b@eB\\}@`@o@fAeAhGuEr@c@CU'

def decode_polyline(polyline_str):
    index, lat, lng = 0, 0, 0
    coordinates = []
    changes = {'latitude': 0, 'longitude': 0}

    # Coordinates have variable length when encoded, so just keep
    # track of whether we've hit the end of the string. In each
    # while loop iteration, a single coordinate is decoded.
    while index < len(polyline_str):
        # Gather lat/lon changes, store them in a dictionary to apply them later
        for unit in ['latitude', 'longitude']: 
            shift, result = 0, 0

            while True:
                byte = ord(polyline_str[index]) - 63
                index+=1
                result |= (byte & 0x1f) << shift
                shift += 5
                if not byte >= 0x20:
                    break

            if (result & 1):
                changes[unit] = ~(result >> 1)
            else:
                changes[unit] = (result >> 1)

        lat += changes['latitude']
        lng += changes['longitude']

        coordinates.append((lat / 100000.0, lng / 100000.0))

    return coordinates


def get_coord_distance(user_location, path_points):
     
    # Approximate radius of earth in km
    R = 6373.0

    user_lat = radians(user_location[0])
    user_lon = radians(user_location[1])

    for index, point in enumerate(path_points):
        
        closest_lat = radians(point[0])
        closest_lon = radians(point[1])

        dlon = closest_lon - user_lon
        dlat = closest_lat - user_lat

        a = sin(dlat / 2)**2 + cos(user_lat) * cos(closest_lat) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c

        if distance < 0.1:
             print(f"Point {index} is less than 100m from user")
             return distance
        else:
             return "No points less than 100m found"

decoded_polyline = decode_polyline(polyline)

user_location = (51.582465, -0.225788)

get_coord_distance(user_location= user_location, path_points= decoded_polyline)
