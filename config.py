import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Weather API
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NWS_POINTS_URL_TEMPLATE = "https://api.weather.gov/points/{lat},{lon}"
NWS_USER_AGENT = "weather-tool/1.0"
