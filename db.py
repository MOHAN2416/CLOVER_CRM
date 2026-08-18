import mysql.connector
from mysql.connector import pooling
import sys
import os
from dotenv import load_dotenv

# Load variables from .env into os.environ (no-op on Render where vars are injected)
load_dotenv()


# ─────────────────────────────────────────────────────────────
# Pull credentials from environment variables.
# On Render: set these in the dashboard under Environment → Add
# Environment Variable.
# For local development: they fall back to your local MySQL setup.
# ─────────────────────────────────────────────────────────────
db_config = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "CloverPass123!"),
    "database": os.environ.get("DB_NAME",     "crm_db")
}

# Pre-initialize pool to None
connection_pool = None

try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="crm_pool",
        pool_size=5,
        **db_config
    )
    print("[✓] Database connection pool initialized successfully.")
except mysql.connector.Error as err:
    print(f"\n❌ DATABASE CONFIGURATION ERROR: {err}")
    print("Please check your DB_HOST, DB_USER, DB_PASSWORD, DB_NAME environment variables.")
    # Exit gracefully instead of letting the app start up broken
    sys.exit(1)

def get_db_connection():
    """Fetches a reusable database connection from the pool."""
    if connection_pool is None:
        raise ConnectionError("Database connection pool was never initialized properly.")
    return connection_pool.get_connection()