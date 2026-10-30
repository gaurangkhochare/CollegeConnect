import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()


def get_db_connection():
    connection_kwargs = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'collegeconnect'),
        'port': int(os.getenv('DB_PORT', '3306')),
    }
    return mysql.connector.connect(**connection_kwargs)
