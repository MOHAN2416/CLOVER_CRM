import os, re
import glob

app_file = 'app.py'
with open(app_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add flask-cors and remove render_template
content = content.replace('from flask import Flask, render_template, jsonify, request, Response, session, redirect, url_for', 'from flask import Flask, jsonify, request, Response, session, redirect, url_for\nfrom flask_cors import CORS')

# Add CORS and session cookie config
target = "app.secret_key = 'clover_system_encryption_token_secret_2026'"
replacement = """app.secret_key = 'clover_system_encryption_token_secret_2026'

CORS(app, supports_credentials=True)
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True
"""
content = content.replace(target, replacement)

# Remove GET method from UI routes and replace render_template with JSON
content = content.replace("methods=['GET', 'POST']", "methods=['POST']")
content = content.replace("    return render_template('login.html')", "    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405")
content = content.replace("    return render_template('signup.html')", "    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405")
content = content.replace("    return render_template('reset_password.html')", "    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405")
content = content.replace("    return render_template('join.html')", "    return jsonify({'status': 'error', 'message': 'Method not allowed'}), 405")
content = content.replace("    return render_template('index.html')", "    return jsonify({'status': 'success', 'message': 'API is running'}), 200")

with open(app_file, 'w', encoding='utf-8') as f:
    f.write(content)

# Frontend Refactoring
frontend_dir = 'frontend/templates'
for html_file in glob.glob(f'{frontend_dir}/*.html'):
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Inject API_BASE_URL config
    if 'const API_BASE_URL' not in html:
        html = html.replace('<head>', '<head>\n    <script>const API_BASE_URL = "http://127.0.0.1:5000";</script>')
    
    # Update fetch calls to use API_BASE_URL and credentials
    html = re.sub(r"fetch\((['\"])/", r"fetch(API_BASE_URL + \g<1>/", html)
    html = re.sub(r"fetch\(([^,]+),\s*\{", r"fetch(\1, {\n                credentials: 'include',", html)

    # For any fetch without options
    html = re.sub(r"fetch\((API_BASE_URL[^)]+)\)(?!\s*\{)", r"fetch(\1, {credentials: 'include'})", html)
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html)
        
# For js files
static_dir = 'frontend/static/js'
for js_file in glob.glob(f'{static_dir}/*.js'):
    with open(js_file, 'r', encoding='utf-8') as f:
        js = f.read()
        
    js = re.sub(r"fetch\((['\"])/", r"fetch(API_BASE_URL + \g<1>/", js)
    js = re.sub(r"fetch\(([^,]+),\s*\{", r"fetch(\1, {\n        credentials: 'include',", js)

    with open(js_file, 'w', encoding='utf-8') as f:
        f.write(js)

print('Refactoring complete.')
