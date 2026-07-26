import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

def train_and_save_model():
    # Ensure model directory exists
    os.makedirs(os.path.join("backend", "app"), exist_ok=True)
    
    # Load dataset
    data_path = os.path.join("data", "railway_crowd_data.csv")
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Please run generate_data.py first.")
        
    df = pd.read_csv(data_path)
    
    # Extract numerical hour from time_slot (e.g. '08:00' -> 8)
    df['hour'] = df['time_slot'].apply(lambda x: int(x.split(':')[0]))
    
    # Define features and target
    features = ['source', 'destination', 'day_of_week', 'hour', 'is_weekend']
    target = 'crowd_level'
    
    X = df[features]
    y = df[target]
    
    # Split dataset into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Define categorical and numerical features
    categorical_features = ['source', 'destination', 'day_of_week']
    
    # Preprocessing pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_features)
        ],
        remainder='passthrough'  # Keep hour and is_weekend as is
    )
    
    # Full machine learning pipeline
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(n_estimators=100, max_depth=12, random_state=42))
    ])
    
    print("Training Random Forest Classifier on crowd data...")
    pipeline.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = pipeline.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Training Complete. Validation Accuracy: {accuracy:.2%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save model pipeline
    model_output_path = os.path.join("backend", "app", "model.joblib")
    joblib.dump(pipeline, model_output_path)
    print(f"\nModel pipeline successfully saved to {model_output_path}!")

if __name__ == "__main__":
    train_and_save_model()

