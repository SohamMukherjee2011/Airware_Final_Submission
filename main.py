import eventlet
eventlet.monkey_patch()
import os
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, redirect, session
from flask_cors import CORS
import requests
from dotenv import load_dotenv
import db
from flask_socketio import SocketIO, emit, join_room
from advisor import create_aqi_chat_agent, user_chat, build_initial_context
from realtime_aqi import realtime_aqi
from realtime_weather import realtime_weather, geocode_city_to_latlon
from analyzer import save_analysis_to_file, geminiForAnalysis, fetch_results
import json
load_dotenv()
db.config()
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIRS = [
    BASE_DIR / "frontend" / "dist",
    BASE_DIR / "frontend" / "build"
]
STATIC_DIR = next((p for p in FRONTEND_DIRS if p.exists()), None)
import dotenv
dotenv.load_dotenv()
# Environment keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

ALLOWED_ORIGINS = "*"
app = Flask(__name__, static_folder=None)
CORS(app, resources={r"/api/*": {"origins": ALLOWED_ORIGINS}})
app.secret_key = '$&@(*FH#%&RUIF#%())'
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading'
)
# ---- Helpers ----
def error_json(message, status=500):
    return jsonify({"error": message}), status

def reverse_geocode(lat, lon):
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
    r = requests.get(url, headers={"User-Agent": "AirAware"})
    if r.status_code == 200:
        data = r.json()
        return (
            data.get("address", {}).get("city") or
            data.get("address", {}).get("town") or
            data.get("address", {}).get("village") or
            data.get("display_name")
        )
    return "Unknown"

def call_get(url, params=None, timeout=15):
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as he:
        # return HTTP error JSON where possible
        raise
    except Exception:
        # bubble up for general handling
        raise
# SocketIO Routes

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')
    emit('connected', {'status': 'Connected to AQI Assistant'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

@socketio.on('join')
def handle_join(data):
    user_id = data.get('userId')
    if user_id:
        join_room(user_id)
        print(f'User {user_id} joined room')
@socketio.on('user_message')
def handle_user_message(data):
    """
    Receives user message, calls Gemini API, and emits assistant response
    Expected data: { userId?: string, text: string, meta?: {...} }
    """
    print(f'Received user_message: {data}')
    
    user_id = data.get('userId')
    text = data.get('text', '')
    meta = data.get('meta', {})
    with open(f"analysis_outputs/analysis_{user_id}.json", "r") as f:
        analysis_json = json.load(f)
    chat = create_aqi_chat_agent(analysis_json)
    data = user_chat(chat, text)
    
    if not text:
        emit('assistant_message', {
            'text': 'Please provide a message.',
            'timestamp': datetime.utcnow().isoformat(),
            'from': 'assistant',
            'error': True
        })
    
    emit('assistant_message', {
                'text': data,
                'timestamp': datetime.utcnow().isoformat(),
                'from': 'assistant'
            })
# ---- Static + multipage routing ----
if STATIC_DIR:
    STATIC_DIR = STATIC_DIR.resolve()
    app.logger.info(f"Serving frontend from: {STATIC_DIR}")

    MULTIPAGE_FILES = ["auth.html", "dashboard.html", "onboarding.html", "profile.html"]

    # Serve /static/assets/<file> -> dist/assets/<file>
    @app.route("/static/assets/<path:filename>")
    def serve_static_assets(filename):
        assets_dir = STATIC_DIR / "assets"
        return send_from_directory(assets_dir, filename)

    # Serve other top-level static files requested under /static/* (favicon.ico etc)
    @app.route("/static/<path:filename>")
    def serve_static_root(filename):
        return send_from_directory(STATIC_DIR, filename)
    @app.route("/")
    @app.route("/auth")
    def auth_page():
        if "username" in session:
            return redirect("/dashboard")
        return send_from_directory(STATIC_DIR, "auth.html")
    @app.route("/dashboard")
    def dash_page():
        if "username" not in session:
            return redirect("/auth")
        return send_from_directory(STATIC_DIR, "dashboard.html")


    # Serve named pages: /auth, /dashboard, /onboarding
    @app.route("/<page_name>")
    def serve_html_page(page_name):
        filename = f"{page_name}.html"
        if filename in MULTIPAGE_FILES:
            return send_from_directory(STATIC_DIR, filename)
        return error_json("Page not found", 404)

    # Root -> auth (you can change to onboarding.html if you prefer)

else:
    @app.route("/")
    def no_frontend():
        return "<h1>No frontend build found in /frontend/dist or /frontend/build</h1>"

@app.route("/api/auth/signup", methods=["POST"])
def api_signup():
    try:
        data = request.get_json()
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        fname = data.get('firstname')
        lname = data.get('lastname')
        db.signupInsert(username, email, password, fname, lname)
        session["username"] = username
        return jsonify({
            "success": True,
            "message": "User created successfully",
            "user_id": username
        })

    except Exception as e:
        return error_json(str(e), 400)

@app.route("/api/onboarding", methods=["POST"])
def api_onboarding():
    try:
        data = request.get_json()
        user_id = data.get("username")
        location = data.get("location")
        age_group = data.get("ageGroup")
        is_sensitive = data.get("isSensitive", False)
        morning_summary = data.get("morningSummary", False)
        threshold_alerts = data.get("thresholdAlerts", False)
        commute_alerts = data.get("commuteAlerts", False)
        enable_notifications = data.get("enableNotifications", True)
        route_start = data.get('routeStart')
        route_end = data.get('routeEnd')
        start_latlon = geocode_city_to_latlon(route_start)
        end_latlon = geocode_city_to_latlon(route_end)
        print(start_latlon[0], end_latlon[0])
        route_start_lat = start_latlon[0]
        route_end_lat = end_latlon[0]
        route_start_lng = start_latlon[1]
        route_end_lng = end_latlon[1]
        db.updateOnboarding(user_id, location, age_group, is_sensitive,
                     morning_summary, threshold_alerts, commute_alerts,
                     enable_notifications, route_start_lat, route_start_lng, 
           route_end_lat, route_end_lng)

        return jsonify({"success": True, "message": "Onboarding updated!"})

    except Exception as e:
        print(e)
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    try:
        data = request.get_json()
        email = data.get("email")
        password = data.get("password")
        user = db.showField("email", email)[0]
        if user[4] == password:
            session["username"] = user[0]
            return jsonify({
            "success": True,
            "message": "Login successful",
            "user": {
                "email": email,
                "username": user[0]
            }
        })
    except Exception as e:
        return error_json(str(e), 401)
@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect("/auth")

@app.route("/api/profile", methods=["GET"])
def api_profile():
    username = session['username']
    if not username:
        return jsonify({"error": "username required"}), 400

    user = db.showField("username", username)
    if not user or len(user) == 0:
        return jsonify({"error": "User not found"}), 404

    user = user[0]

    result = {
        "username": user[0],
        "email": user[1],
        "location": user[7],
        "age_group": user[5],
        "firstname": user[2],
        "lastname": user[3],
        "is_sensitive": bool(user[6]),
    }
    return jsonify(result)
@app.route("/api/recommendations/route-exposure", methods=["GET"])
def api_route_exposure():
    """
    Returns route‑exposure recommendations to the frontend.
    You will later populate the response.
    """
    user = db.showField('username', session['username'])[0]

    USER_DATA = {
   'Name': user[2] + ' ' + user[3],
   'Age': user[5],
   'Health_Issues': user[6],
   'Residence': user[7],
    }
    start_latlon = (user[8], user[9])
    end_latlon = (user[10], user[11])
    USER_ROUTE = [
        start_latlon, end_latlon
    ]
    save_analysis_to_file(user_id=user[0])
    with open(f"analysis_outputs/analysis_{user[0]}.json", "r") as f:
        analysis_json = json.load(f)

    chat = create_aqi_chat_agent(analysis_json)
    oneliner = user_chat(chat, 'Based off all the details give me detailed advice for today in one single sentence, without any formatting')
    try:
        # You will replace this dictionary with your real data.
        dummy_response = {
    "success": True,
  "riskLevel": "High",
  "distanceFactor": 0.85,
  "advice": 
    oneliner
  ,
  "timestamp": datetime.now()
}


        return jsonify(dummy_response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---- Weather endpoint (Open‑Meteo) ----
@app.route("/api/weather", methods=["GET"])
def api_weather():
    try:
        lat = request.args.get("lat")
        lon = request.args.get("lon")
        if not lat or not lon:
            return error_json("Missing coordinates", 400)

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            # request hourly humidity and apparent_temperature (apparent temp key is 'apparent_temperature')
            "hourly": ["relativehumidity_2m", "apparent_temperature", "weathercode"],
            "timezone": "auto"
        }

        data = call_get(url, params=params)

        current = data.get("current_weather", {})
        hourly = data.get("hourly", {})

        # Safely find index of current time in hourly.time (fallback to 0)
        def find_index():
            try:
                return hourly.get("time", []).index(current.get("time"))
            except Exception:
                return 0

        idx = find_index()

        def safe_at(list_or_none, i=idx):
            if isinstance(list_or_none, list) and len(list_or_none) > i:
                return list_or_none[i]
            return None

        humidity = safe_at(hourly.get("relativehumidity_2m"))
        feels_like = safe_at(hourly.get("apparent_temperature"))

        # Simple mapping from weathercode to human label (extend as needed)
        weather_map = {
            0: "Clear",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            61: "Light rain",
            71: "Light snow",
            80: "Rain showers"
        }
        condition = weather_map.get(current.get("weathercode"), "Unknown")

        return jsonify({
            "temp": current.get("temperature"),
            "feelsLike": feels_like,
            "humidity": humidity,
            "windSpeed": current.get("windspeed"),
            "description": condition,
            "time": current.get("time")
        })
    except Exception as e:
        return error_json(str(e), 500)

# ---- Location (reverse geocoding) ----
@app.route("/api/location", methods=["GET"])
def api_location():
    try:
        lat = request.args.get("lat")
        lon = request.args.get("lon")
        if not lat or not lon:
            return error_json("Missing coordinates", 400)

        url = "https://geocoding-api.open-meteo.com/v1/reverse"
        params = {"latitude": lat, "longitude": lon, "count": 1}
        data = call_get(url, params=params)
        results = data.get("results") or []
        if not results:
            return error_json("Location not found", 404)
        loc = results[0]
        return jsonify({
            "city": loc.get("name"),
            "country": loc.get("country"),
            "lat": loc.get("latitude"),
            "lon": loc.get("longitude")
        })
    except Exception as e:
        return error_json(str(e), 500)

# ---- AQI (Open‑Meteo Air Quality) ----
@app.route("/api/aqi", methods=["GET"])
def api_aqi():
    try:
        lat = request.args.get("lat")
        lon = request.args.get("lon")
        if not lat or not lon:
            return error_json("Missing coordinates", 400)

        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": lat,
            "longitude": lon,
            # pass hourly as list (requests will encode multiple hourly parameters)
            "hourly": [
                "us_aqi",
                "pm10",
                "pm2_5",
                "carbon_monoxide",
                "nitrogen_dioxide",
                "ozone",
                "sulphur_dioxide"
            ],
            "timezone": "auto"
        }

        data = call_get(url, params=params)

        # If API returns an error
        if data.get("error"):
            reason = data.get("reason") or "AQI data unavailable"
            return error_json(reason, 502)

        hourly = data.get("hourly", {})

        # helper for safe extraction
        def safe(arr):
            return arr[0] if isinstance(arr, list) and len(arr) > 0 else None
        location_name = reverse_geocode(lat, lon)
        result = {
            "location": location_name,
            "aqi": safe(hourly.get("us_aqi")),
            "pm25": safe(hourly.get("pm2_5")),
            "pm10": safe(hourly.get("pm10")),
            "co": safe(hourly.get("carbon_monoxide")),
            "no2": safe(hourly.get("nitrogen_dioxide")),
            "o3": safe(hourly.get("ozone")),
            "so2": safe(hourly.get("sulphur_dioxide")),
            "time": safe(hourly.get("time"))
        }
        return jsonify(result)
    except Exception as e:
        return error_json(str(e), 500)

# ---- AI advice (Gemini) ----
@app.route("/api/ai/advice", methods=["POST"])
def api_ai_advice():
    try:
        if not GEMINI_API_KEY:
            return error_json("GEMINI_API_KEY not configured", 500)
        body = request.get_json() or {}
        aqi = body.get("aqi")
        weather = body.get("weather", {})
        profile = body.get("userProfile", {})

        prompt = f"""
AQI: {aqi}
Temperature: {weather.get('temperature')}
Wind: {weather.get('windSpeed')}
User: Age={profile.get('age')}, Sensitivity={profile.get('sensitivity')}
Provide a brief advisory.
"""

        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        resp = requests.post(gemini_url, json=payload, timeout=30)
        resp.raise_for_status()
        out = resp.json()
        advice = out.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text")
        return jsonify({"advice": advice, "timestamp": datetime.utcnow().isoformat()})
    except Exception as e:
        return error_json(str(e), 500)

# ---- Errors ----
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404

# ---- Run ----
if __name__ == "__main__":


    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 5000))
    )
