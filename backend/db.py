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
db_host = os.environ.get("DB_HOST", "localhost")
db_port = int(os.environ.get("DB_PORT", 3306))

db_config = {
    "host":     db_host,
    "port":     db_port,
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "CloverPass123!"),
    "database": os.environ.get("DB_NAME",     "crm_db")
}

# TiDB Cloud and remote cloud databases enforce SSL/TLS encryption
if db_host not in ("localhost", "127.0.0.1"):
    try:
        import certifi
        db_config["ssl_ca"] = certifi.where()
        db_config["ssl_verify_cert"] = True
        db_config["ssl_verify_identity"] = True
    except Exception:
        # Fallback if certifi is unavailable
        db_config["ssl_disabled"] = False


# Pre-initialize pool to None
connection_pool = None

try:
    connection_pool = pooling.MySQLConnectionPool(
        pool_name="crm_pool",
        pool_size=5,
        **db_config
    )
    print("[OK] Database connection pool initialized successfully.")
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