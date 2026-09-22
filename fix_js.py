import re

with open('frontend/static/js/script.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Fix template literals to include API_BASE_URL if they start with /api/
js = re.sub(r"fetch\(`(/api/[^`]+)`", r"fetch(API_BASE_URL + `\1`", js)

# For any fetch without options, add {credentials: 'include'}
js = re.sub(r"fetch\((API_BASE_URL[^,)]+)\)(?!\s*\{)", r"fetch(\1, {credentials: 'include'})", js)

with open('frontend/static/js/script.js', 'w', encoding='utf-8') as f:
    f.write(js)
