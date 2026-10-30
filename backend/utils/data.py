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
db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(db_url)

# Load Excel file
excel_path = "TT EXCEL.xlsx"
xls = pd.ExcelFile(excel_path)

all_dfs = []

# Process each sheet in the Excel workbook
for sheet_name in xls.sheet_names:
    if sheet_name == "EXCS":
        # EXCS sheet has a different layout/header offset
        df = pd.read_excel(excel_path, sheet_name=sheet_name, skiprows=3, header=None)
        df = df.iloc[:, :8]  # Keep first 8 columns
        df.columns = [
            "BRANCH",
            "YEAR",
            "DIV",
            "SUBJECT",
            "PROF",
            "TIME",
            "LOCATION",
            "DAY",
        ]
    else:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)

    all_dfs.append(df)

# Combine all sheets into a single DataFrame
combined_df = pd.concat(all_dfs, ignore_index=True)

# Data Cleaning & Preprocessing
# 1. Drop rows where BRANCH or entire row is completely empty/NaN
combined_df = combined_df.dropna(subset=["BRANCH"])

# 2. Fill missing or NaN values with safe placeholders to satisfy NOT NULL constraints
combined_df["DIV"] = combined_df["DIV"].fillna("N/A").astype(str)
combined_df["SUBJECT"] = combined_df["SUBJECT"].fillna("UNKNOWN").astype(str)
combined_df["PROF"] = combined_df["PROF"].fillna("TBD").astype(str)
combined_df["TIME"] = combined_df["TIME"].fillna("TBD").astype(str)
combined_df["LOCATION"] = combined_df["LOCATION"].fillna("ONLINE").astype(str)
combined_df["DAY"] = combined_df["DAY"].fillna("TBD").astype(str)

# 3. Map DataFrame columns to match the MySQL 'timetable' table column names
df_to_insert = pd.DataFrame(
    {
        "branch": combined_df["BRANCH"].str.strip(),
        "year_level": combined_df["YEAR"].astype(str).str.strip(),
        "division": combined_df["DIV"].str.strip(),
        "day": combined_df["DAY"].str.strip(),
        "time_slot": combined_df["TIME"].str.strip(),
        "subject_code": combined_df["SUBJECT"].str.strip(),
        "prof_code": combined_df["PROF"].str.strip(),
        "location": combined_df["LOCATION"].str.strip(),
    }
)

# Optional: Remove any leftover rows with empty strings in vital fields
df_to_insert = df_to_insert[df_to_insert["branch"] != ""]

print(f"Total rows to insert: {len(df_to_insert)}")

# Insert data into MySQL table 'timetable'
try:
    df_to_insert.to_sql(
        name="timetable",
        con=engine,
        if_exists="append",  # Appends rows to the existing table
        index=False,
        chunksize=500,  # Batch inserts for better performance
    )
    print("Successfully inserted all timetable records into MySQL database!")
except Exception as e:
    print(f"Error occurred while inserting data: {e}")
