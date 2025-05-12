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
    geocode_resp = requests.get(geocode_url, params=params,
                                headers={"User-Agent": NWS_USER_AGENT})
    geocode_resp.raise_for_status()
    geo = geocode_resp.json()
    if not geo:
        return f"No geocoding result for '{location}'."
    lat, lon = geo[0]["lat"], geo[0]["lon"]

    # Get forecast endpoint from NWS Points API
    points_url = NWS_POINTS_URL_TEMPLATE.format(lat=lat, lon=lon)
    headers = {"User-Agent": NWS_USER_AGENT}
    points_resp = requests.get(points_url, headers=headers)
    points_resp.raise_for_status()
    forecast_url = points_resp.json()["properties"]["forecast"]

    # Fetch the forecast
    forecast_resp = requests.get(forecast_url, headers=headers)
    forecast_resp.raise_for_status()
    periods = forecast_resp.json()["properties"]["periods"]
    if not periods:
        return "No forecast data available."

    # Use the first period (current)
    current = periods[0]
    name = current["name"]
    short = current["shortForecast"]
    temp = current["temperature"]
    unit = current["temperatureUnit"]
    updated = current.get("startTime", "")[:19].replace("T", " ")
    return f"{name}: {short}, {temp}°{unit} (as of {updated} UTC)"