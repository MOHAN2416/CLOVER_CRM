from flask import Flask, render_template
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'), 
            static_folder=os.path.join(BASE_DIR, 'static'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/<path:page>')
def serve_page(page):
    try:
        return render_template(f'{page}.html')
    except:
        return "Page not found", 404

if __name__ == '__main__':
    print("Starting frontend server on port 8000...")
    app.run(host='0.0.0.0', port=8000, debug=False)
