College Enquiry Chatbot

This repository contains a minimal Flask-based college enquiry chatbot implemented in prc_chatbot.py.

Features
- Web chat UI at http://localhost:5000/
- Keyword-based FAQ matching
- Simple admin page to add FAQs at http://localhost:5000/admin (no auth; secure before production)
- API endpoint: POST /message { "message": "..." } -> { "reply": "..." }
- GET /faqs returns current FAQs JSON

Requirements
- Python 3.8+
- pip install flask

Run
1. Install Flask: pip install flask
2. Run: python "prc chatbot\prc_chatbot.py"
3. Open http://localhost:5000/ in your browser

Notes
- FAQs are stored in-memory. To persist across restarts, modify the script to save/load from a JSON file or connect to a database.
- For an LLM-powered fallback, integrate an API in find_faq_reply and handle API keys securely.

