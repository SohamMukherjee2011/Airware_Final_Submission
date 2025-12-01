from realtime_aqi import realtime_aqi
from route_exposure import calculate_exposure
from realtime_weather import realtime_weather
from config import get_settings
from google import genai
from pathlib import Path
from typing import Dict
from datetime import datetime
import uuid
import json
import jsonschema

# NOTE THE USER INFORMATION IS TO BE INTEGRATED BY SOHAM
# IMPORT FROM THE DATABASE AND PASS IT ONTO THE PARAMETERS IN THE FECTCH_RESULTS() FUCNTION
# THIS IS A TEST SCRIPT AND USED TEST LOCATION (Kolkata) AND TEST User DATA:
# {
#   Name: ASAF,
#   Age: 58,
#   Health_Issues: ['Asthama', 'Respiratory Issues'],
#   Residence: Kolkata,
# }
# TEST ROUTE: Sova Bazar -> Salt Lake Sector V Everyday
# TEST ROUTE COORDs (later to be integrated with backend map data): 
# [
#   {"lat": 22.5950, "lon": 88.3610},
#   {"lat": 22.5890, "lon": 88.3650},
#   {"lat": 22.5820, "lon": 88.3700},
#   {"lat": 22.5750, "lon": 88.3780},
#   {"lat": 22.5680, "lon": 88.3850},
#   {"lat": 22.5620, "lon": 88.3920},
#   {"lat": 22.5672, "lon": 88.3715},   
#   {"lat": 22.5721, "lon": 88.3903},   
#   {"lat": 22.5801, "lon": 88.4013},  
#   {"lat": 22.5871, "lon": 88.4079},   
#   {"lat": 22.5904, "lon": 88.4156},   
#   {"lat": 22.5813, "lon": 88.4298}    
# ]

USER_DATA = {
   'Name': 'ASAF',
   'Age': 58,
   'Health_Issues': ['Asthama', 'Respiratory Issues'],
   'Residence': 'Kolkata',
}
USER_ROUTE = [
  {"lat": 22.5950, "lon": 88.3610},
  {"lat": 22.5890, "lon": 88.3650},
  {"lat": 22.5820, "lon": 88.3700},
  {"lat": 22.5750, "lon": 88.3780},
  {"lat": 22.5680, "lon": 88.3850},
  {"lat": 22.5620, "lon": 88.3920},
  {"lat": 22.5672, "lon": 88.3715},   
  {"lat": 22.5721, "lon": 88.3903},   
  {"lat": 22.5801, "lon": 88.4013},  
  {"lat": 22.5871, "lon": 88.4079},   
  {"lat": 22.5904, "lon": 88.4156},   
  {"lat": 22.5813, "lon": 88.4298}    
]

def fetch_results(user_data, route):
    location = user_data['Residence']
    health_hazard = user_data['Health_Issues']
    user_age = user_data['Age']
    route_summary = {
        "route_id": uuid.uuid4().hex,
        "exposure": calculate_exposure(route),
        "units": "ug·hr/m3",
        "start_lat": route[0]["lat"],
        "start_lon": route[0]["lon"],
        "end_lat": route[-1]["lat"],
        "end_lon": route[-1]["lon"]
    }
    realtime = realtime_aqi(location)
    curWeather = realtime_weather(route[0]["lat"], route[0]["lon"])
    return {
        "user": {
            "age": user_age,
            "health_issues": health_hazard,
            "residence": location
        },
        "current": {
            "current_aqi": realtime,
            "current_weather": curWeather
        },
        "route": route_summary,
        "weather": curWeather
    }

api_key = get_settings().GEMINI_API_KEY
SCHEMA_PATH = Path(__file__).resolve().parent / "analysis_schema.json"
with open(SCHEMA_PATH, "r") as f:
    SCHEMA = json.load(f)
client = genai.Client(api_key=api_key)

def geminiForAnalysis(compFetch: Dict):
    system_prompt = f"""
    You are an AQI analysis agent. 
    Based of the data (about the current AQI, Weather and User) provided,
    analyse the situation carefuly,
    Respond ONLY with valid JSON.
    DO NOT write anything outside of the JSON object.

    Schema:
    {json.dumps(SCHEMA)}

    Input:
    {json.dumps(compFetch)}
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[system_prompt],
        config={
            "response_mime_type": "application/json"
        }
    )
    analysis = json.loads(response.text)
    jsonschema.validate(analysis, SCHEMA)
    return analysis

def save_analysis_to_file(user_id="default"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_{user_id}.json"
    compact_Fetch = fetch_results(user_data=USER_DATA, route=USER_ROUTE)
    analysis = geminiForAnalysis(compact_Fetch)
    path = Path(__file__).resolve().parent / "analysis_outputs"
    path.mkdir(exist_ok=True)

    full_path = path / filename

    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=4)
    return str(full_path)