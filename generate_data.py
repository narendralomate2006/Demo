import csv
import random
import os

# Define constant parameters
STATIONS = ['Pune', 'Shivajinagar', 'Pimpri', 'Chinchwad']
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
TIME_SLOTS = [f"{hour:02d}:00" for hour in range(24)]

def get_crowd_level(day_of_week, hour):
    is_weekend = 1 if day_of_week in ['Saturday', 'Sunday'] else 0
    
    if is_weekend == 0:
        # Weekdays
        # Peak hours: 8-10 AM (8, 9, 10) and 5-8 PM (17, 18, 19, 20)
        if (8 <= hour <= 10) or (17 <= hour <= 20):
            # High crowds
            return random.choices(['High', 'Medium'], weights=[0.90, 0.10])[0]
        # Mid-day normal hours
        elif 11 <= hour <= 16:
            return random.choices(['Medium', 'Low', 'High'], weights=[0.80, 0.15, 0.05])[0]
        # Off-peak hours
        else:
            return random.choices(['Low', 'Medium'], weights=[0.90, 0.10])[0]
    else:
        # Weekends
        # Weekend crowd characteristics - moderate travel in late morning and evening
        if (11 <= hour <= 15) or (17 <= hour <= 19):
            return random.choices(['Medium', 'Low'], weights=[0.70, 0.30])[0]
        else:
            return random.choices(['Low', 'Medium'], weights=[0.95, 0.05])[0]

def generate_dataset(file_path, num_rows=1000):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Write headers
        writer.writerow(['source', 'destination', 'day_of_week', 'time_slot', 'is_weekend', 'crowd_level'])
        
        for _ in range(num_rows):
            source = random.choice(STATIONS)
            # Destination should be different from source
            dest_options = [s for s in STATIONS if s != source]
            destination = random.choice(dest_options)
            
            day = random.choice(DAYS_OF_WEEK)
            time_slot = random.choice(TIME_SLOTS)
            hour = int(time_slot.split(':')[0])
            
            is_weekend = 1 if day in ['Saturday', 'Sunday'] else 0
            crowd_level = get_crowd_level(day, hour)
            
            writer.writerow([source, destination, day, time_slot, is_weekend, crowd_level])

if __name__ == "__main__":
    output_path = os.path.join("data", "railway_crowd_data.csv")
    print(f"Generating synthetic dataset with 1000 rows at: {output_path}...")
    generate_dataset(output_path, num_rows=1000)
    print("Dataset generation complete!")
