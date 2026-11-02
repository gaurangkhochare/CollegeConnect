import json
import pandas as pd
from sqlalchemy import create_engine

# Configuration for MySQL connection
# Replace 'username', 'password', 'localhost', and '3306' with your actual MySQL credentials
DB_USER = "username"
DB_PASSWORD = "password"
DB_HOST = "localhost"
DB_PORT = "3306"
DB_NAME = "collegeconnect"

# Create database connection string using SQLAlchemy and PyMySQL
db_url = f"mysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_url)

# Load JSON file
json_path = 'path/to/file.json'
with open(json_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# Convert to pandas DataFrame for cleaning and mapping
df = pd.DataFrame(raw_data)

# Data Cleaning & Preprocessing
# 1. Drop rows with null or invalid locations
df = df.dropna(subset=['location'])

# 2. Clean and map status (handling numeric status codes or text values)
# The table uses an ENUM('available','maintenance','inactive')
status_map = {0: 'available', 1: 'maintenance', 2: 'inactive', '0': 'available', '1': 'maintenance', '2': 'inactive'}
df['status'] = df['status'].map(status_map).fillna('available')

# 3. Clean booleans and other fields to match schema constraints
df['has_ac'] = df['has_ac'].astype(bool)
df['has_smart_board'] = df['has_smart_board'].astype(bool)
df['has_wifi'] = df['has_wifi'].astype(bool)
df['capacity'] = pd.to_numeric(df['capacity'], errors='coerce').fillna(0).astype(int)
df['capacity'] = df['capacity'].apply(lambda x: None if x == 0 else x) # Set 0 capacity to NULL if preferred

# 4. Filter and select columns matching the 'classrooms' table definition
# We exclude 'id' to let MySQL auto-increment it, or include it if you want to keep original IDs.
df_to_insert = pd.DataFrame({
    'location': df['location'].str.strip(),
    'block': df['block'].astype(str).str.strip(),
    'room_number': df['room_number'].astype(str).str.strip(),
    'capacity': df['capacity'],
    'has_ac': df['has_ac'],
    'has_smart_board': df['has_smart_board'],
    'has_wifi': df['has_wifi'],
    'status': df['status']
})

# Drop duplicate locations if any exist to respect the UNIQUE constraint on 'location'
df_to_insert = df_to_insert.drop_duplicates(subset=['location'])

print(f"Total unique classroom records to insert: {len(df_to_insert)}")

# Insert data into MySQL table 'classrooms'
try:
    df_to_insert.to_sql(
        name='classrooms',
        con=engine,
        if_exists='append',  # Appends rows to the existing table
        index=False,
        chunksize=500        # Batch inserts for better performance
    )
    print("Successfully inserted all classroom records into MySQL database!")
except Exception as e:
    print(f"Error occurred while inserting data: {e}")