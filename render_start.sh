#!/usr/bin/env bash
# render_start.sh — Run on Render to train model (if needed) then start server

echo "=== Railway Crowd Monitoring System — Render Startup ==="

# Train model if it doesn't exist (first deploy)
if [ ! -f "backend/app/model.joblib" ]; then
    echo "No model found. Generating dataset and training model..."
    python generate_data.py
    python train_model.py
    echo "Model training complete!"
else
    echo "Model already exists. Skipping training."
fi

# Start FastAPI server
echo "Starting FastAPI backend server..."
uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT"
