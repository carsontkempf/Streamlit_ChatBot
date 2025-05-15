import requests
from langchain_core.tools import tool

from config import NOMINATIM_URL, NWS_POINTS_URL_TEMPLATE, NWS_USER_AGENT

@tool(
    description="Get current weather for a location using the National Weather Service API."
)
def weather_tool(location: str) -> str:
    """
    Retrieve current weather for the given location (e.g. 'Maryville, MO' or ZIP code)
    using the NWS Points and Forecast endpoints.
    """
    # Geocode the location via Nominatim OpenStreetMap
    geocode_url = NOMINATIM_URL
    params = {"q": location, "format": "json", "limit": 1}
    try: # Add try-except for network requests
        geocode_resp = requests.get(geocode_url, params=params,
                                    headers={"User-Agent": NWS_USER_AGENT}, timeout=10)
        geocode_resp.raise_for_status() # Will raise an HTTPError for bad responses (4XX or 5XX)
        geo = geocode_resp.json()
    except requests.exceptions.RequestException as e: # Use logging for errors
        return f"Error during geocoding: {e}"
    except ValueError as e: # Handles JSON decoding errors, use logging
        return f"Error decoding geocoding JSON response: {e}"

    if not geo:
        return f"No geocoding result for '{location}'."
    
    # It's possible for geo[0] to not exist if geo is an empty list but not None
    if not isinstance(geo, list) or len(geo) == 0 or "lat" not in geo[0] or "lon" not in geo[0]:
        return f"Geocoding result for '{location}' is malformed or missing lat/lon."
        
    lat, lon = geo[0]["lat"], geo[0]["lon"]

    # Get forecast endpoint from NWS Points API
    points_url = NWS_POINTS_URL_TEMPLATE.format(lat=lat, lon=lon)
    headers = {"User-Agent": NWS_USER_AGENT}
    try: # Add try-except for network requests
        points_resp = requests.get(points_url, headers=headers, timeout=10) # Added timeout
        points_resp.raise_for_status()
        points_data = points_resp.json() # Use logging for errors
    except requests.exceptions.RequestException as e:
        return f"Error fetching NWS points data: {e}"
    except ValueError as e: # Handles JSON decoding errors, use logging
        return f"Error decoding NWS points JSON response: {e}"

    # Check for expected structure in points_data
    if not (points_data.get("properties") and points_data["properties"].get("forecast")):
        return "Could not retrieve forecast URL from NWS points data."
    forecast_url = points_data["properties"]["forecast"]


    # Fetch the forecast
    try: # Add try-except for network requests
        forecast_resp = requests.get(forecast_url, headers=headers, timeout=10) # Added timeout
        forecast_resp.raise_for_status()
        forecast_data = forecast_resp.json() # Use logging for errors
    except requests.exceptions.RequestException as e:
        return f"Error fetching NWS forecast: {e}"
    except ValueError as e: # Handles JSON decoding errors, use logging
        return f"Error decoding NWS forecast JSON response: {e}"

    # Check for expected structure in forecast_data
    if not (forecast_data.get("properties") and forecast_data["properties"].get("periods")):
        return "Forecast data is missing expected 'periods' information."
        
    periods = forecast_data["properties"]["periods"]
    # Use logging for warnings/info about data structure
    if not periods: # Check if periods list is empty
        return "No forecast data available in periods."

    # Use the first period (current)
    current = periods[0]
    name = current.get("name", "N/A") # Use .get for safer dictionary access
    short = current.get("shortForecast", "N/A")
    temp = current.get("temperature", "N/A")
    unit = current.get("temperatureUnit", "N/A")
    # Ensure startTime exists and is a string before slicing
    raw_updated_time = current.get("startTime", "")
    updated = ""
    if isinstance(raw_updated_time, str) and len(raw_updated_time) >= 19:
        updated = raw_updated_time[:19].replace("T", " ")
    else:
        updated = "Timestamp N/A"
        
    return f"{name}: {short}, {temp}°{unit} (as of {updated} UTC)"
