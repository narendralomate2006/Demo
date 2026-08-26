import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import joblib

app = FastAPI(title="Railway Crowd Monitoring System API", version="1.0.0")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "railway_crowd_data.csv"))

class AlternativeOption(BaseModel):
    mode: str
    route: str
    duration_mins: int
    estimated_fare_inr: int
    frequency: str
    status: str

class PredictionRequest(BaseModel):
    source: str
    destination: str
    day_of_week: str
    time_slot: str

class PredictionResponse(BaseModel):
    source: str
    destination: str
    day_of_week: str
    time_slot: str
    is_weekend: int
    predicted_crowd_level: str
    alternative_options: Optional[List[AlternativeOption]] = None

# Route-wise alternative travel options
# Uses frozenset so order of source/destination doesn't matter
ALTERNATIVES = {
    frozenset(["Pune", "Shivajinagar"]): [
        {"mode": "Metro", "route": "Purple Line (Direct)", "duration_mins": 8, "estimated_fare_inr": 15, "frequency": "Every 7 mins", "status": "Fastest Option — AC, No Traffic"},
        {"mode": "Bus (PMPML)", "route": "Route 102/112 via Wellesley Rd", "duration_mins": 20, "estimated_fare_inr": 10, "frequency": "Every 12 mins", "status": "Most Economical"},
        {"mode": "Cab / Auto", "route": "Via Wellesley Road", "duration_mins": 15, "estimated_fare_inr": 70, "frequency": "Immediate Booking", "status": "Door-to-door comfort"},
    ],
    frozenset(["Pune", "Pimpri"]): [
        {"mode": "Metro", "route": "Purple Line (Direct to Pimpri)", "duration_mins": 25, "estimated_fare_inr": 25, "frequency": "Every 7 mins", "status": "Fastest — Bypasses Highway Traffic"},
        {"mode": "Bus (PMPML)", "route": "Route 312 via Old Pune-Mumbai Hwy", "duration_mins": 45, "estimated_fare_inr": 20, "frequency": "Every 15 mins", "status": "Regular City Bus"},
        {"mode": "Cab / Auto", "route": "Via Old Highway / NH 48", "duration_mins": 35, "estimated_fare_inr": 220, "frequency": "Immediate Booking", "status": "Flexible private transit"},
    ],
    frozenset(["Pune", "Chinchwad"]): [
        {"mode": "Metro + Auto", "route": "Purple Line to Pimpri → Auto to Chinchwad", "duration_mins": 35, "estimated_fare_inr": 40, "frequency": "Every 10 mins", "status": "Efficient Transit Mix"},
        {"mode": "Bus (PMPML)", "route": "Route 311/312 via Old Hwy", "duration_mins": 55, "estimated_fare_inr": 25, "frequency": "Every 15 mins", "status": "Standard City Bus"},
        {"mode": "Cab / Auto", "route": "Direct via NH 48", "duration_mins": 40, "estimated_fare_inr": 280, "frequency": "Immediate Booking", "status": "Comfortable Door-to-Door"},
    ],
    frozenset(["Shivajinagar", "Pimpri"]): [
        {"mode": "Metro", "route": "Purple Line (Direct)", "duration_mins": 18, "estimated_fare_inr": 20, "frequency": "Every 7 mins", "status": "Fastest Option — AC, No Traffic"},
        {"mode": "Bus (PMPML)", "route": "Route 312 via Old Highway", "duration_mins": 35, "estimated_fare_inr": 15, "frequency": "Every 15 mins", "status": "Regular Bus Route"},
        {"mode": "Cab / Auto", "route": "Via Old Pune-Mumbai Hwy", "duration_mins": 25, "estimated_fare_inr": 180, "frequency": "Immediate Booking", "status": "Private Ride"},
    ],
    frozenset(["Shivajinagar", "Chinchwad"]): [
        {"mode": "Metro + Auto", "route": "Purple Line to Pimpri → Auto to Chinchwad", "duration_mins": 30, "estimated_fare_inr": 35, "frequency": "Every 10 mins", "status": "Avoids Highway Congestion"},
        {"mode": "Bus (PMPML)", "route": "Route 311 via Old Highway", "duration_mins": 45, "estimated_fare_inr": 20, "frequency": "Every 15 mins", "status": "Economical Ride"},
        {"mode": "Cab / Auto", "route": "Via NH 48", "duration_mins": 30, "estimated_fare_inr": 240, "frequency": "Immediate Booking", "status": "Private Ride"},
    ],
    frozenset(["Pimpri", "Chinchwad"]): [
        {"mode": "Auto Rickshaw", "route": "Direct via Link Road", "duration_mins": 10, "estimated_fare_inr": 50, "frequency": "Immediate Booking", "status": "Fastest Local Alternative"},
        {"mode": "Bus (PMPML)", "route": "Route 312 / Local Bus", "duration_mins": 15, "estimated_fare_inr": 10, "frequency": "Every 8 mins", "status": "Very Economical Local Ride"},
        {"mode": "Cab / Auto", "route": "Direct via highway", "duration_mins": 10, "estimated_fare_inr": 80, "frequency": "Immediate Booking", "status": "Private Ride"},
    ],
}

def get_alternatives(source: str, destination: str) -> List[dict]:
    key = frozenset([source, destination])
    return ALTERNATIVES.get(key, [
        {"mode": "Bus (PMPML)", "route": "Local Connecting Bus", "duration_mins": 40, "estimated_fare_inr": 20, "frequency": "Every 20 mins", "status": "Public Transit"},
        {"mode": "Cab / Auto", "route": "Via Local Highways", "duration_mins": 30, "estimated_fare_inr": 150, "frequency": "Immediate Booking", "status": "Flexible Private Transit"},
    ])

# Load model pipeline
def load_model():
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    return None

@app.get("/stations")
def get_stations():
    return ["Pune", "Shivajinagar", "Pimpri", "Chinchwad"]

@app.post("/predict", response_model=PredictionResponse)
def predict_crowd(request: PredictionRequest):
    stations = get_stations()
    if request.source not in stations or request.destination not in stations:
        raise HTTPException(status_code=400, detail="Invalid source or destination station.")
    if request.source == request.destination:
        raise HTTPException(status_code=400, detail="Source and destination cannot be the same.")

    try:
        hour = int(request.time_slot.split(":")[0])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid time slot format. Use 'HH:00'.")

    is_weekend = 1 if request.day_of_week in ["Saturday", "Sunday"] else 0

    # Try loading the ML model
    model = load_model()
    if model is None:
        # Fallback to rule-based logic if model isn't trained yet
        if is_weekend == 0:
            if (8 <= hour <= 10) or (17 <= hour <= 20):
                predicted = "High"
            elif 11 <= hour <= 16:
                predicted = "Medium"
            else:
                predicted = "Low"
        else:
            if (11 <= hour <= 15) or (17 <= hour <= 19):
                predicted = "Medium"
            else:
                predicted = "Low"
    else:
        input_data = pd.DataFrame([{
            "source": request.source,
            "destination": request.destination,
            "day_of_week": request.day_of_week,
            "hour": hour,
            "is_weekend": is_weekend
        }])
        try:
            prediction = model.predict(input_data)[0]
            predicted = str(prediction)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

    # Always include alternative options
    alternatives = get_alternatives(request.source, request.destination)

    return {
        "source": request.source,
        "destination": request.destination,
        "day_of_week": request.day_of_week,
        "time_slot": request.time_slot,
        "is_weekend": is_weekend,
        "predicted_crowd_level": predicted,
        "alternative_options": alternatives,
    }

DEFAULT_HISTORICAL_STATS = {
    "crowd_distribution": {"Low": 420, "Medium": 290, "High": 290},
    "hourly_stats": {
        0: 1.08, 1: 1.06, 2: 1.14, 3: 1.02, 4: 1.07, 5: 1.15, 6: 1.10, 7: 1.06,
        8: 2.33, 9: 2.38, 10: 2.60, 11: 1.88, 12: 1.78, 13: 1.86, 14: 1.86, 15: 1.85,
        16: 1.72, 17: 2.58, 18: 2.35, 19: 2.54, 20: 2.42, 21: 1.07, 22: 1.04, 23: 1.09
    },
    "busy_stations": {"Pune": 110, "Shivajinagar": 85, "Pimpri": 55, "Chinchwad": 40},
    "weekend_vs_weekday": {
        "weekday_avg": 1.88,
        "weekend_avg": 1.35
    }
}

@app.get("/historical-stats")
def get_historical_stats():
    try:
        if not os.path.exists(DATA_PATH):
            return DEFAULT_HISTORICAL_STATS

        df = pd.read_csv(DATA_PATH)
        df = df.dropna(subset=['time_slot', 'crowd_level', 'source'])
        df = df[df['time_slot'].astype(str).str.contains(':')]
        df['hour'] = df['time_slot'].apply(lambda x: int(str(x).split(':')[0]))

        crowd_distribution_raw = df['crowd_level'].value_counts().to_dict()
        crowd_distribution = {
            "Low": int(crowd_distribution_raw.get("Low", 0)),
            "Medium": int(crowd_distribution_raw.get("Medium", 0)),
            "High": int(crowd_distribution_raw.get("High", 0))
        }

        mapping = {"Low": 1, "Medium": 2, "High": 3}
        df['crowd_score'] = df['crowd_level'].map(mapping).fillna(1)

        hourly_means = df.groupby('hour')['crowd_score'].mean().round(2).to_dict()
        hourly_stats = {h: float(hourly_means.get(h, 1.0)) for h in range(24)}

        high_crowd_df = df[df['crowd_level'] == 'High']
        busy_raw = high_crowd_df.groupby('source').size().to_dict()
        busy_stations = {s: int(busy_raw.get(s, 0)) for s in get_stations()}

        weekend_means = df.groupby('is_weekend')['crowd_score'].mean().round(2).to_dict()

        return {
            "crowd_distribution": crowd_distribution,
            "hourly_stats": hourly_stats,
            "busy_stations": busy_stations,
            "weekend_vs_weekday": {
                "weekday_avg": float(weekend_means.get(0, 1.8)),
                "weekend_avg": float(weekend_means.get(1, 1.3))
            }
        }
    except Exception as e:
        print(f"Stats calculation error, returning default: {e}")
        return DEFAULT_HISTORICAL_STATS