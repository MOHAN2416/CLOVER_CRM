import mysql.connector
from mysql.connector import pooling
import sys

# Configure database credentials
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "CloverPass123!",  # <-- Ensure this matches the password from Step 1
    "database": "crm_db"
}

# Pre-initialize pool to None
connection_pool = None

try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="crm_pool",
        pool_size=5,
        **db_config
    )
    print("Database connection pool initialized successfully.")
except mysql.connector.Error as err:
    print(f"\n❌ DATABASE CONFIGURATION ERROR: {err}")
    print("Please check your password configuration or user credentials inside db.py.")
    # Exit gracefully instead of letting the app start up broken
    sys.exit(1)

def get_db_connection():
    """Fetches a reusable database connection from the pool."""
    if connection_pool is None:
        raise ConnectionError("Database connection pool was never initialized properly.")
    return connection_pool.get_connection()