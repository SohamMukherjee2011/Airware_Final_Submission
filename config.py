from functools import lru_cache
import os
import dotenv

dotenv.load_dotenv()

class Settings:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    AQICN_TOKEN = os.getenv('WAQI_API_TOKEN',"")
    OPENAQ_TOKEN = os.getenv('OPENAQ_API_TOKEN')
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "8.0"))
@lru_cache
def get_settings():
    return Settings()
