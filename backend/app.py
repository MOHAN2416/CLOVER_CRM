from flask import Flask, jsonify, request, Response, session, redirect, url_for
from flask_cors import CORS
import mysql.connector
from db import get_db_connection
import csv
import io
from groq import Groq
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load variables from .env into os.environ (no-op on Render where vars are injected)
load_dotenv()

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
# Environment-driven configuration.
# On Render: set SECRET_KEY and FRONTEND_URL in the dashboard under
# Environment → Add Environment Variable.
# ─────────────────────────────────────────────────────────────
app.secret_key = os.environ.get('SECRET_KEY', 'clover_system_encryption_token_secret_2026')

# FRONTEND_URL is your Vercel deployment URL e.g. https://clover-crm.vercel.app
# Defaults to localhost for local testing.
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:8000')
CORS(app, supports_credentials=True, origins=[FRONTEND_URL, 'http://127.0.0.1:8000', 'http://localhost:8000', 'http://11.12.22.120:8000'])
# For local HTTP development, cookies cannot be Secure=True with SameSite=None
if 'localhost' in FRONTEND_URL or '127.0.0.1' in FRONTEND_URL:
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False
else:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True


def ensure_admin_user():
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = 'admin@gmail.com'")
        admin = cursor.fetchone()
        if not admin:
            password_hash = generate_password_hash('admin123')
            # Insert into users
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                ('admin', 'admin@gmail.com', password_hash)
            )
            # Insert into sales_reps
            cursor.execute(
                "INSERT INTO sales_reps (name, email) VALUES (%s, %s)",
                ('admin', 'admin@gmail.com')
            )
            connection.commit()
            print("[INFO] Admin user successfully initialized.")
    except Exception as e:
        print(f"[WARNING] Failed to initialize admin user: {e}")
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

ensure_admin_user()

@app.route('/api/login', methods=['POST'])
def login():
    """Serves and processes the secure session authorization portal."""
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({"status": "error", "message": "Email and password are required."}), 400
            
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['user_id']
                session['username'] = user['username']
                session['email'] = user['email']
                
                # Look up corresponding rep_id in sales_reps
                cursor.execute("SELECT rep_id FROM sales_reps WHERE email = %s", (email,))
                rep = cursor.fetchone()
                if rep:
                    session['rep_id'] = rep['rep_id']
                else:
                    session['rep_id'] = None
                    
                return jsonify({"status": "success", "message": "Login successful!"})
            else:
                return jsonify({"status": "error", "message": "Invalid email or password."}), 401
        except Exception as e:
            return jsonify({"status": "error", "message": f"Login database error: {str(e)}"}), 500
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
                
    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405

@app.route('/api/signup', methods=['POST'])
def signup():
    """Serves and processes the sales representative registration portal."""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return jsonify({"status": "error", "message": "All fields are required."}), 400
            
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Check if username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                return jsonify({"status": "error", "message": "Username is already taken."}), 400
                
            # Check if email already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"status": "error", "message": "Email is already registered."}), 400
                
            password_hash = generate_password_hash(password)
            
            # Insert into users table
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                (username, email, password_hash)
            )
            # Also insert into sales_reps table to represent this user as a sales representative!
            cursor.execute(
                "INSERT INTO sales_reps (name, email) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name=VALUES(name)",
                (username, email)
            )
            connection.commit()
            return jsonify({"status": "success", "message": "Registration successful! Redirecting to login..."})
        except Exception as e:
            if connection: connection.rollback()
            return jsonify({"status": "error", "message": f"Registration failed: {str(e)}"}), 500
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
                
    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405

@app.route('/api/logout')
def logout():
    """Destroys the active session and returns a success response."""
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully"}), 200

@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Serves and processes the sales representative credential recovery portal."""
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({"status": "error", "message": "Email and new password are required."}), 400
            
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({"status": "error", "message": "No registered user found with that email address."}), 404
                
            password_hash = generate_password_hash(password)
            
            # Update password in the database
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE email = %s",
                (password_hash, email)
            )
            connection.commit()
            
            # Update in the user's log (stdout + Flask logger)
            app.logger.info(f"User Log: Password updated successfully for email: {email}")
            print(f"User Log: Password updated successfully for email: {email}")
            
            return jsonify({"status": "success", "message": "Password updated successfully! Redirecting to login..."})
        except Exception as e:
            if connection: connection.rollback()
            return jsonify({"status": "error", "message": f"Password update failed: {str(e)}"}), 500
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
            
    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405



@app.route('/join')
def render_public_lead_form():
    """Renders the public-facing inbound marketing registration page."""
    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405


@app.route('/api/webhook/lead', methods=['POST'])
def external_form_webhook():
    """
    Acts as a secure data-ingestion gateway. Receives incoming JSON payloads
    from public forms, normalizes fields, and inserts them straight into MySQL.
    """
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    
    if not name or not email:
        return jsonify({"status": "error", "message": "Name and email are required fields."}), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # FIXED: Balanced 7 placeholders to cleanly match the 7 column variables
        query = """
        INSERT INTO accounts (name, email, phone, company, source, status, rep_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            name,
            email,
            data.get('phone', '').strip() or None,
            data.get('company', '').strip() or 'Independent',
            data.get('source', 'Inbound Web Form'),
            'Lead',
            None  # <-- FIXED: Explicitly maps NULL to unassigned sales reps
        )
        
        cursor.execute(query, values)
        connection.commit()

        return jsonify({"status": "success", "message": "Thank you! Your information has been securely submitted."}), 201

    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"status": "error", "message": f"Ingestion error: {str(e)}"}), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

        
@app.route('/api/search', methods=['POST'])
def execute_semantic_search():
    """Accepts natural text criteria and executes local vector space filtering mapping."""
    data = request.get_json()
    query_text = data.get('query', '').strip()
    
    if not query_text:
        return jsonify({"status": "error", "message": "Search string text required"}), 400

    try:
        # 1. Dynamically sync latest state updates into the vector space
        index_all_accounts(get_db_connection)
        
        # 2. Extract matching IDs using vector coordinate distances
        matched_ids = semantic_search_pipeline(query_text, num_results=3)
        
        if not matched_ids:
            return jsonify({"status": "success", "results": []}), 200

        # 3. Pull full records from MySQL matching those specific IDs
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        format_strings = ','.join(['%s'] * len(matched_ids))
        cursor.execute(f"SELECT account_id, name, company, source, status FROM accounts WHERE account_id IN ({format_strings})", tuple(matched_ids))
        results = cursor.fetchall()
        
        return jsonify({"status": "success", "results": results}), 200
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'connection' in locals() and connection: connection.close()

@app.route('/api/ai/suggest-email/<int:account_id>', methods=['GET'])
def ai_suggest_email(account_id):
    """
    Queries local MySQL data and streams local LLM inference tokens 
    via a Server-Sent Events (SSE) generator channel.
    """
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        query = """
        SELECT a.name, a.company, a.source, a.status, COALESCE(d.deal_value, 0) as deal_value, COALESCE(d.stage, 'None') as stage
        FROM accounts a
        LEFT JOIN deals d ON a.account_id = d.account_id
        WHERE a.account_id = %s
        LIMIT 1;
        """
        cursor.execute(query, (account_id,))
        account_data = cursor.fetchone()

        if not account_data:
            return "Account not found", 404

        # CRITICAL FIX: Explicit System Prompt to lock down model role identity
        system_instructions = (
            "You are an automated B2B Sales Assistant embedded inside 'Clover CRM'. "
            "Your job is to draft a short, punchy email follow-up. Do NOT mention Alibaba. "
            "Do NOT sign off as Qwen. Sign off strictly as 'Clover CRM Sales Agent'."
        )
        
        user_prompt = f"Write a contextual email follow-up for {account_data['name']} at {account_data['company'] or 'Independent'}. Deal Stage: {account_data['stage']}. Value: INR {float(account_data['deal_value'])}."

        # Define an internal generator function to stream text segments using Groq (or fallback)
        def generate_tokens():
            groq_key = os.environ.get("GROQ_API_KEY")
            if not groq_key or groq_key == "your_groq_api_key_here":
                # Fallback template if Groq is not configured
                fallback = (
                    f"Subject: Follow-up regarding {account_data['name']} / {account_data['company'] or 'Partnership'}\n\n"
                    f"Dear {account_data['name']},\n\n"
                    f"I hope this note finds you well. I am writing to follow up on our recent conversation regarding your account with Clover CRM.\n\n"
                    f"We noticed that your deal is currently at the '{account_data['stage']}' stage. Our team is ready to assist you in moving forward and ensuring you have everything you need to reach your objectives.\n\n"
                    f"Would you be open to a brief 10-minute check-in later this week?\n\n"
                    f"Best regards,\n"
                    f"Clover CRM Sales Team"
                )
                yield fallback
                return

            try:
                # Initialize lightweight Groq Cloud Client
                client = Groq(api_key=groq_key)
                selected_model = 'llama-3.1-8b-instant'
                
                response_stream = client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": user_prompt}
                    ],
                    stream=True
                )
                
                for chunk in response_stream:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
            except Exception as e:
                yield f"Error generating email: {str(e)}"

        # Return a live response streaming wrapper
        return Response(generate_tokens(), mimetype='text/plain')

    except Exception as err:
        return f"Local Engine Error: {str(err)}", 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.route('/api/accounts/bulk-upload', methods=['POST'])
def bulk_upload_accounts():
    """
    Parses a CSV file stream, validates column structures, and performs
    an optimized transactional bulk insert into the accounts table.
    """
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in the request"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"status": "error", "message": "Invalid format. Only CSV files are supported."}), 400

    connection = None
    cursor = None
    try:
        # Stream decode the uploaded binary text
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        # Standardize fieldnames to lowercase to support case-insensitive headers
        if csv_reader.fieldnames:
            csv_reader.fieldnames = [f.strip().lower() for f in csv_reader.fieldnames]
            
        # Verify basic headers match expected database schema
        required_headers = ['name', 'email']
        if not all(header in csv_reader.fieldnames for header in required_headers):
            return jsonify({"status": "error", "message": "CSV missing required headers: 'name' and 'email'"}), 400

        bulk_data = []
        for row_idx, row in enumerate(csv_reader, start=1):
            name = row.get('name', '').strip()
            email = row.get('email', '').strip()
            
            # Simple row-level validation
            if not name or not email:
                return jsonify({"status": "error", "message": f"Validation failed at row {row_idx}: Missing name or email."}), 400

            # Map the csv structure to match our accounts schema rules
            bulk_data.append((
                name,
                email,
                row.get('phone', '').strip() or None,
                row.get('company', '').strip() or None,
                row.get('source', 'CSV Import').strip() or 'CSV Import',
                'Lead', # Default state engine boundary configuration
                None    # Initially unassigned sales rep
            ))

        if not bulk_data:
            return jsonify({"status": "error", "message": "The uploaded CSV file is empty."}), 400

        # Execute Atomic Transactional Database Ingestion
        connection = get_db_connection()
        cursor = connection.cursor()
        
        insert_query = """
        INSERT INTO accounts (name, email, phone, company, source, status, rep_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        # executemany passes data in a single optimized stream drop
        cursor.executemany(insert_query, bulk_data)
        connection.commit()

        return jsonify({
            "status": "success", 
            "message": f"Successfully ingested {len(bulk_data)} records into the pipeline state engine!"
        }), 201

    except mysql.connector.Error as err:
        if connection: connection.rollback() # Rollback if database breaks midway
        return jsonify({"status": "error", "message": f"Database transaction failed: {str(err)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Parsing failure: {str(e)}"}), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.route('/api/tasks', methods=['POST'])
def add_task():
    """Schedules a new follow-up interaction task for a sales rep."""
    data = request.get_json()
    
    if not data or not data.get('account_id') or not data.get('rep_id') or not data.get('due_date'):
        return jsonify({"status": "error", "message": "Missing required fields (Account, Rep, or Due Date)"}), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = """
        INSERT INTO tasks (account_id, rep_id, task_type, due_date, remarks, is_completed)
        VALUES (%s, %s, %s, %s, %s, FALSE)
        """
        values = (
            data.get('account_id'),
            data.get('rep_id'),
            data.get('task_type', 'Call'),
            data.get('due_date'),
            data.get('remarks', '')
        )
        cursor.execute(query, values)
        connection.commit()

        return jsonify({"status": "success", "message": "Task scheduled successfully!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": f"Database error: {str(err)}"}), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route('/api/tasks/<int:task_id>/complete', methods=['PUT'])
def complete_task(task_id):
    """Updates a task's status flag to completed, removing it from pending views."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        query = "UPDATE tasks SET is_completed = TRUE WHERE task_id = %s"
        cursor.execute(query, (task_id,))
        connection.commit()

        return jsonify({"status": "success", "message": "Task marked as completed!"}), 200

    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": f"Database error: {str(err)}"}), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()   

@app.route('/')
def index():
    """Serves the main frontend CRM dashboard."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return jsonify({'status': 'success', 'message': 'API is running'}), 200

@app.route('/api/profile')
def get_profile():
    """Retrieves authenticated representative's details and performance analytics."""
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    username = session.get('username')
    email = session.get('email')
    
    if email == 'admin@gmail.com':
        connection = None
        cursor = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Count total leads
            cursor.execute("SELECT COUNT(*) as total_leads FROM accounts")
            total_leads = cursor.fetchone()['total_leads']
            
            # Get deals won and total revenue
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN stage = 'Won' THEN 1 END) as deals_won,
                    COALESCE(SUM(CASE WHEN stage = 'Won' THEN deal_value ELSE 0 END), 0) as total_revenue
                FROM deals
            """)
            deal_stats = cursor.fetchone()
            
            return jsonify({
                "status": "success",
                "data": {
                    "username": "CEO / Admin",
                    "email": email,
                    "rep_id": "System Owner",
                    "deals_won": deal_stats['deals_won'],
                    "total_revenue": float(deal_stats['total_revenue']),
                    "total_leads": total_leads
                }
            })
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
        finally:
            if cursor: cursor.close()
            if connection: connection.close()
            
    rep_id = session.get('rep_id')
    if not rep_id:
        return jsonify({
            "status": "success",
            "data": {
                "username": username,
                "email": email,
                "rep_id": None,
                "deals_won": 0,
                "total_revenue": 0.0,
                "total_leads": 0
            }
        })
        
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Count total leads
        cursor.execute("SELECT COUNT(*) as total_leads FROM accounts WHERE rep_id = %s", (rep_id,))
        total_leads = cursor.fetchone()['total_leads']
        
        # Get deals won and total revenue
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN stage = 'Won' THEN 1 END) as deals_won,
                COALESCE(SUM(CASE WHEN stage = 'Won' THEN deal_value ELSE 0 END), 0) as total_revenue
            FROM deals
            WHERE rep_id = %s
        """, (rep_id,))
        deal_stats = cursor.fetchone()
        
        return jsonify({
            "status": "success",
            "data": {
                "username": username,
                "email": email,
                "rep_id": rep_id,
                "deals_won": deal_stats['deals_won'],
                "total_revenue": float(deal_stats['total_revenue']),
                "total_leads": total_leads
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.route('/api/admin/sales-reps', methods=['POST'])
def admin_add_rep():
    """Allows Admin/CEO to register a new sales representative account."""
    if 'user_id' not in session or session.get('email') != 'admin@gmail.com':
        return jsonify({"status": "error", "message": "Unauthorized admin action"}), 403
        
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not name or not email or not password:
        return jsonify({"status": "error", "message": "All fields are required."}), 400
        
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Check if username or email already registered
        cursor.execute("SELECT * FROM users WHERE username = %s", (name,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Username is already taken."}), 400
            
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({"status": "error", "message": "Email is already registered."}), 400
            
        password_hash = generate_password_hash(password)
        
        # Insert into users
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, password_hash)
        )
        
        # Insert into sales_reps
        cursor.execute(
            "INSERT INTO sales_reps (name, email) VALUES (%s, %s)",
            (name, email)
        )
        
        connection.commit()
        return jsonify({"status": "success", "message": "Sales representative account created successfully."})
    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()

@app.route('/api/admin/sales-reps/<email>', methods=['DELETE'])
def admin_delete_rep(email):
    """Allows Admin/CEO to delete a sales representative account."""
    if 'user_id' not in session or session.get('email') != 'admin@gmail.com':
        return jsonify({"status": "error", "message": "Unauthorized admin action"}), 403
        
    if email == 'admin@gmail.com':
        return jsonify({"status": "error", "message": "Cannot delete the admin account."}), 400
        
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Delete from sales_reps and users
        cursor.execute("DELETE FROM sales_reps WHERE email = %s", (email,))
        cursor.execute("DELETE FROM users WHERE email = %s", (email,))
        
        connection.commit()
        return jsonify({"status": "success", "message": "Sales representative account deleted successfully."})
    except Exception as e:
        if connection: connection.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close()
        if connection: connection.close()



@app.route('/api/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """
    Executes our advanced, hardened SQL queries to fetch real-time analytics.
    Fixes name-collisions, includes task flags, and calculates true conversion rates.
    Supports rep-level isolation if rep_id is set in session or request arguments.
    """
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Unauthorized session"}), 401
        
    is_admin = (session.get('email') == 'admin@gmail.com')
    if is_admin:
        rep_id = None
    else:
        rep_id = session.get('rep_id') or request.args.get('rep_id', type=int)

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        # Setting dictionary=True maps rows to Python dictionaries: {'column_name': value}
        cursor = connection.cursor(dictionary=True)
        
        metrics = {}

        # Query 1: True Conversion Rate (Handles Lead Status logic perfectly)
        if rep_id:
            conversion_query = """
            SELECT 
                ROUND(100.0 * SUM(CASE WHEN status = 'Active Customer' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS conversion_rate
            FROM accounts
            WHERE rep_id = %s;
            """
            cursor.execute(conversion_query, (rep_id,))
        else:
            conversion_query = """
            SELECT 
                ROUND(100.0 * SUM(CASE WHEN status = 'Active Customer' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 2) AS conversion_rate
            FROM accounts;
            """
            cursor.execute(conversion_query)
        metrics['conversion_rate'] = cursor.fetchone()['conversion_rate'] or 0.0

        # Query 2: Top Customers by Revenue (Grouped by ID to eliminate name collision)
        if rep_id:
            top_customers_query = """
            SELECT a.account_id, a.name, SUM(d.deal_value) AS total_revenue
            FROM accounts a
            JOIN deals d ON a.account_id = d.account_id
            WHERE d.stage = 'Won' AND a.rep_id = %s
            GROUP BY a.account_id, a.name
            ORDER BY total_revenue DESC
            LIMIT 5;
            """
            cursor.execute(top_customers_query, (rep_id,))
        else:
            top_customers_query = """
            SELECT a.account_id, a.name, SUM(d.deal_value) AS total_revenue
            FROM accounts a
            JOIN deals d ON a.account_id = d.account_id
            WHERE d.stage = 'Won'
            GROUP BY a.account_id, a.name
            ORDER BY total_revenue DESC
            LIMIT 5;
            """
            cursor.execute(top_customers_query)
        metrics['top_customers'] = cursor.fetchall()

        # Query 3: Active Pending Follow-Ups (Ignores completed/stale tasks)
        if rep_id:
            pending_tasks_query = """
            SELECT t.task_id, a.name AS account_name, t.task_type, DATE_FORMAT(t.due_date, '%Y-%m-%d %H:%i') AS due_date, t.remarks
            FROM tasks t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE t.is_completed = FALSE AND t.rep_id = %s
            ORDER BY t.due_date ASC;
            """
            cursor.execute(pending_tasks_query, (rep_id,))
        else:
            pending_tasks_query = """
            SELECT t.task_id, a.name AS account_name, t.task_type, DATE_FORMAT(t.due_date, '%Y-%m-%d %H:%i') AS due_date, t.remarks
            FROM tasks t
            JOIN accounts a ON t.account_id = a.account_id
            WHERE t.is_completed = FALSE
            ORDER BY t.due_date ASC;
            """
            cursor.execute(pending_tasks_query)
        metrics['pending_tasks'] = cursor.fetchall()

        # Query 4: Sales Leaderboard (Our core differentiator showing rep performance)
        leaderboard_query = """
        SELECT 
            r.rep_id,
            r.name AS rep_name,
            r.email,
            COUNT(CASE WHEN d.stage = 'Won' THEN 1 END) AS deals_won,
            SUM(CASE WHEN d.stage = 'Won' THEN d.deal_value ELSE 0 END) AS total_revenue
        FROM sales_reps r
        LEFT JOIN deals d ON r.rep_id = d.rep_id
        GROUP BY r.rep_id, r.name, r.email
        ORDER BY total_revenue DESC;
        """
        cursor.execute(leaderboard_query)
        metrics['leaderboard'] = cursor.fetchall()

        # Query 5: Fetch 5 Most Recent Accounts (Shows new leads instantly)
        if rep_id:
            recent_leads_query = """
            SELECT account_id, name, company, status, source
            FROM accounts
            WHERE rep_id = %s
            ORDER BY created_at DESC
            LIMIT 5;
            """
            cursor.execute(recent_leads_query, (rep_id,))
        else:
            recent_leads_query = """
            SELECT account_id, name, company, status, source
            FROM accounts
            ORDER BY created_at DESC
            LIMIT 5;
            """
            cursor.execute(recent_leads_query)
        metrics['recent_leads'] = cursor.fetchall()

        # Query 6: Automated "Next-Best-Action" Urgency Engine
        if rep_id:
            urgency_query = """
            SELECT 
                a.account_id,
                a.name AS account_name,
                a.company,
                a.status,
                (
                    -- Rule 1: Neglected leads (Raw leads with no tasks logged at all)
                    (CASE WHEN a.status = 'Lead' AND (SELECT COUNT(*) FROM tasks WHERE account_id = a.account_id) = 0 THEN 20 ELSE 0 END) +
                    
                    -- Rule 2: High-Value Deals Stalled in Negotiation (No recent task updates)
                    (CASE WHEN EXISTS (SELECT 1 FROM deals WHERE account_id = a.account_id AND stage = 'Negotiation') THEN 50 ELSE 0 END) +
                    
                    -- Rule 3: Active Overdue Tasks present
                    (CASE WHEN EXISTS (SELECT 1 FROM tasks WHERE account_id = a.account_id AND is_completed = FALSE AND due_date < NOW()) THEN 40 ELSE 0 END)
                ) AS urgency_score
            FROM accounts a
            WHERE a.rep_id = %s
            HAVING urgency_score > 0
            ORDER BY urgency_score DESC
            LIMIT 3;
            """
            cursor.execute(urgency_query, (rep_id,))
        else:
            urgency_query = """
            SELECT 
                a.account_id,
                a.name AS account_name,
                a.company,
                a.status,
                (
                    -- Rule 1: Neglected leads (Raw leads with no tasks logged at all)
                    (CASE WHEN a.status = 'Lead' AND (SELECT COUNT(*) FROM tasks WHERE account_id = a.account_id) = 0 THEN 20 ELSE 0 END) +
                    
                    -- Rule 2: High-Value Deals Stalled in Negotiation (No recent task updates)
                    (CASE WHEN EXISTS (SELECT 1 FROM deals WHERE account_id = a.account_id AND stage = 'Negotiation') THEN 50 ELSE 0 END) +
                    
                    -- Rule 3: Active Overdue Tasks present
                    (CASE WHEN EXISTS (SELECT 1 FROM tasks WHERE account_id = a.account_id AND is_completed = FALSE AND due_date < NOW()) THEN 40 ELSE 0 END)
                ) AS urgency_score
            FROM accounts a
            HAVING urgency_score > 0
            ORDER BY urgency_score DESC
            LIMIT 3;
            """
            cursor.execute(urgency_query)
        metrics['urgent_alerts'] = cursor.fetchall()
        metrics['is_admin'] = is_admin

        return jsonify({"status": "success", "data": metrics}), 200

    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": f"Database error: {str(err)}"}), 500
        
    finally:
        # Always close resources to return the connection to the pool
        if cursor:
            cursor.close()
        if connection:
            connection.close()



@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Retrieves all accounts sorted alphabetically for selections."""
    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT account_id, name, company FROM accounts ORDER BY name ASC")
        accounts = cursor.fetchall()
        return jsonify({"status": "success", "data": accounts}), 200
    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": f"Database error: {str(err)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@app.route('/api/accounts', methods=['POST'])
def add_account():
    """
    Accepts JSON data from the frontend form and inserts a new account/lead 
    into the database, maintaining foreign key safety.
    """
    data = request.get_json()
    
    # Basic Validation
    if not data or not data.get('name') or not data.get('email'):
        return jsonify({"status": "error", "message": "Missing required fields (Name/Email)"}), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Insert Query (rep_id can be None/Null if no rep is assigned yet)
        query = """
        INSERT INTO accounts (name, email, phone, company, source, status, rep_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data.get('name'),
            data.get('email'),
            data.get('phone'),
            data.get('company'),
            data.get('source', 'Website'),
            data.get('status', 'Lead'),
            data.get('rep_id') if data.get('rep_id') != "" else None
        )

        cursor.execute(query, values)
        connection.commit() # Crucial for write operations!

        return jsonify({"status": "success", "message": "Account created successfully!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": f"Database error: {str(err)}"}), 500
        
    finally:
        if cursor: cursor.close()
        if connection: connection.close()


@app.route('/api/deals', methods=['POST'])
def add_deal():
    """
    Inserts a new sales opportunity/deal into the database.
    If the stage is 'Won', it automatically upgrades the account status.
    """
    data = request.get_json()
    
    if not data or not data.get('account_id') or not data.get('deal_value'):
        return jsonify({"status": "error", "message": "Missing required fields (Account ID/Value)"}), 400

    connection = None
    cursor = None
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # 1. Insert the Deal
        deal_query = """
        INSERT INTO deals (account_id, rep_id, deal_value, stage)
        VALUES (%s, %s, %s, %s)
        """
        # Convert empty string rep_id to None for database safety
        rep_id = data.get('rep_id') if data.get('rep_id') != "" else None
        
        deal_values = (
            data.get('account_id'),
            rep_id,
            data.get('deal_value'),
            data.get('stage', 'Prospect')
        )
        cursor.execute(deal_query, deal_values)

        # 2. Smart Business Logic Automation:
        # If a deal is 'Won', auto-upgrade the account status to 'Active Customer'
        if data.get('stage') == 'Won':
            update_account_query = """
            UPDATE accounts 
            SET status = 'Active Customer' 
            WHERE account_id = %s
            """
            cursor.execute(update_account_query, (data.get('account_id'),))

        connection.commit()
        return jsonify({"status": "success", "message": "Deal logged successfully!"}), 201

    except mysql.connector.Error as err:
        return jsonify({"status": "error", "message": f"Database error: {str(err)}"}), 500
        
    finally:
        if cursor: cursor.close()
        if connection: connection.close()



if __name__ == '__main__':
    # In production on Render, gunicorn is used instead of this block.
    # This block is only for local development.
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)