try:
    from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session
except ModuleNotFoundError as e:
    # Helpful runtime message when Flask is not installed in the active interpreter
    import sys
    # Raise a clearer, programmatic error instead of exiting the process so callers
    # (tests/IDE/debugger) can handle the failure.
    raise ModuleNotFoundError(
        "Flask is not installed. Install it with: "
        f"{sys.executable} -m pip install flask"
    ) from e
import re
import os
import json
from datetime import datetime, timezone

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or os.environ.get('FLASK_SECRET', 'dev-secret-key')

# Configuration from environment
BRAND_COLOR = os.environ.get('BRAND_COLOR', '#0066cc')
ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
ADMIN_PASS = os.environ.get('ADMIN_PASS', 'password')

# Data persistence
ROOT = os.path.dirname(__file__)
DATA_DIR = os.path.join(ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
FAQS_FILE = os.path.join(DATA_DIR, 'faqs.json')

# Seed FAQ data (used only if no persisted file exists)
FAQS = [
    {
        "id": 1,
        "question": "What undergraduate courses do you offer?",
        "answer": "We offer B.Sc., B.A., B.Com, B.Tech and other undergraduate programmes across multiple departments.",
        "keywords": ["undergraduate", "courses", "bsc", "btech", "ba", "bcom", "programmes", "degrees"]
    },
    {
        "id": 2,
        "question": "How can I apply for admission?",
        "answer": "You can apply online via our admissions portal. Visit /admissions or contact admissions@college.edu for assistance.",
        "keywords": ["apply", "admission", "admissions", "apply online", "application", "enroll", "joining"]
    },
    {
        "id": 3,
        "question": "What are the fees and scholarships available?",
        "answer": "Fee structure depends on the programme. We offer merit and need-based scholarships. Contact finance@college.edu for details.",
        "keywords": ["fees", "scholarship", "scholarships", "fee", "cost", "tuition", "financial aid"]
    },
    {
        "id": 4,
        "question": "When are campus tours and open days?",
        "answer": "Campus tours run every Wednesday and the next open day is on 15th September. Check the events page for updates.",
        "keywords": ["tour", "open day", "campus", "visit", "location", "address"]
    },
    {
        "id": 5,
        "question": "How do I contact the college?",
        "answer": "You can call +1-555-1234 or email info@college.edu. The admissions office is admissions@college.edu.",
        "keywords": ["contact", "phone", "email", "address", "number", "helpline"]
    },
    {
        "id": 6,
        "question": "Greetings & Welcome",
        "answer": "Hello! Welcome to our College Enquiry Helpdesk. How can I assist you today with courses, admissions, fees, or campus tours?",
        "keywords": ["hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening"]
    },
    {
        "id": 7,
        "question": "Thank You & Gratitude",
        "answer": "You're very welcome! Feel free to ask if you have any more questions about admissions, courses, or college life.",
        "keywords": ["thanks", "thank you", "thx", "thankyou", "appreciated", "thank you so much"]
    },
    {
        "id": 8,
        "question": "Goodbye & Farewell",
        "answer": "Goodbye! Have a wonderful day ahead. Reach out to admissions@college.edu anytime if you need further help.",
        "keywords": ["bye", "goodbye", "see you", "cya", "have a good day", "have a nice day"]
    },
    {
        "id": 9,
        "question": "Who are you / Help",
        "answer": "I am the College Enquiry Virtual Assistant! I can help answer your questions about undergraduate courses, admissions, fees, scholarships, and campus visits.",
        "keywords": ["who are you", "what are you", "help", "bot", "assistant"]
    }
]

DEFAULT_REPLY = "I'm sorry, I don't have that information right now. Please contact admissions@college.edu or ask another question."


STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "have", "has", "had", "can", "could", "would",
    "should", "what", "where", "when", "why", "how", "who", "which",
    "you", "your", "i", "me", "my", "we", "our", "us", "they", "them",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
    "and", "or", "but", "if", "not", "so", "this", "that"
}


def find_faq_reply(message: str):
    if not message:
        return None
    text = message.lower().strip()

    # 1. Check exact/multi-word keyword matches with word boundaries (longer keywords prioritized)
    all_kw_matches = []
    for faq in FAQS:
        for kw in faq.get("keywords", []):
            if not kw:
                continue
            pattern = r'\b' + re.escape(kw.lower()) + r'\b'
            if re.search(pattern, text):
                all_kw_matches.append((len(kw), faq["answer"]))

    if all_kw_matches:
        # Sort by keyword length descending so specific multi-word matches take precedence
        all_kw_matches.sort(key=lambda x: x[0], reverse=True)
        return all_kw_matches[0][1]

    # 2. Fallback: match content words from question text (excluding stop words)
    words = set(re.findall(r"\w+", text)) - STOP_WORDS
    if not words:
        return None

    best_faq = None
    max_overlap = 0

    for faq in FAQS:
        qwords = set(re.findall(r"\w+", faq["question"].lower())) - STOP_WORDS
        overlap = len(words & qwords)
        if overlap >= 1 and overlap > max_overlap:
            max_overlap = overlap
            best_faq = faq

    if best_faq:
        return best_faq["answer"]

    return None


def load_faqs():
    global FAQS
    try:
        if os.path.exists(FAQS_FILE):
            with open(FAQS_FILE, 'r', encoding='utf-8') as f:
                FAQS = json.load(f)
        else:
            # save defaults
            save_faqs()
    except Exception:
        # if load fails, keep in-memory defaults
        pass


def save_faqs():
    try:
        with open(FAQS_FILE, 'w', encoding='utf-8') as f:
            json.dump(FAQS, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# Load persisted FAQs on startup
load_faqs()


INDEX_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>College Enquiry Chatbot</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#f6f8fb;--card:#ffffff;--accent:__BRAND_COLOR__;--muted:#6b7280}
    *{box-sizing:border-box}
    body{font-family:Inter,system-ui,Segoe UI,Roboto,Arial; margin:0; background:linear-gradient(180deg,#eef2ff 0%, #f6f8fb 100%); color:#0f172a}
    .container{max-width:1000px;margin:28px auto;padding:20px}
    .hero{display:flex;gap:24px;align-items:flex-start}
    .brand{flex:1}
    .brand h1{margin:0;font-size:28px;color:var(--accent)}
    .brand p{margin:8px 0 0;color:var(--muted)}
    .card{background:var(--card);border-radius:12px;box-shadow:0 6px 18px rgba(2,6,23,0.08);overflow:hidden}
    .chat-wrap{width:420px;display:flex;flex-direction:column}
    #chat{padding:18px;height:520px;overflow-y:auto;background:linear-gradient(180deg,#ffffff 0%,#fbfdff 100%)}
    .composer{display:flex;padding:12px;border-top:1px solid #eef2ff}
    .composer input{flex:1;padding:12px;border-radius:999px;border:1px solid #e6eef8;margin-right:10px}
    .composer button{background:var(--accent);color:#fff;border:none;padding:10px 16px;border-radius:10px;cursor:pointer}
    .msg{display:flex;margin:10px 0;align-items:flex-end}
    .msg.bot{justify-content:flex-start}
    .msg.user{justify-content:flex-end}
    .bubble{max-width:78%;padding:12px 14px;border-radius:14px;line-height:1.3}
    .bot .bubble{background:#f1f7ff;color:#05224a;border-top-left-radius:6px}
    .user .bubble{background:var(--accent);color:white;border-top-right-radius:6px}
    .meta{font-size:12px;color:var(--muted);margin-top:8px}
    .quick{display:flex;gap:8px;margin-top:12px}
    .chip{background:#eef6ff;border-radius:999px;padding:8px 12px;color:var(--accent);cursor:pointer;border:1px solid #e0f0ff}
    .left-col{flex:1}
    .right-col{width:460px}
    .faq-list{padding:16px}
    .faq-item{padding:12px;border-radius:8px;background:#fbfdff;margin-bottom:10px;border:1px solid #eef6ff}
    @media(max-width:900px){.hero{flex-direction:column}.right-col{width:100%}}
  </style>
</head>
<body>
  <div class="container">
    <div class="hero">
      <div class="brand">
        <div style="display:flex;align-items:center;gap:12px">
          <img src="/static/logo.svg" alt="Logo" style="height:48px;width:48px;border-radius:8px;background:rgba(0,0,0,0.03);padding:6px"/>
          <h1 style="margin:0">College Enquiry Chatbot</h1>
        </div>
        <p>Fast answers about courses, admissions, fees and campus life. Chat with our virtual assistant below.</p>
        <div class="meta">Open hours: Mon-Fri 9am–5pm • admissions@college.edu</div>
      </div>

      <div class="card right-col">
        <div id="chat" aria-live="polite"></div>
        <div class="composer">
          <input id="input" placeholder="Ask about courses, admissions, fees or campus tours..." autocomplete="off" />
          <button id="send">Send</button>
        </div>
      </div>
    </div>

    <div style="margin-top:18px;display:flex;gap:18px">
      <div class="left-col">
        <div class="card faq-list">
          <h3 style="margin-top:0">Popular Questions</h3>
          <div class="faq-item"><strong>What undergraduate courses do you offer?</strong><div class="meta">B.Sc., B.A., B.Com, B.Tech and more.</div></div>
          <div class="faq-item"><strong>How can I apply?</strong><div class="meta">Apply online via the admissions portal or email admissions@college.edu.</div></div>
          <div class="faq-item"><strong>Are there scholarships?</strong><div class="meta">Merit and need-based scholarships available.</div></div>
        </div>
      </div>

      <div style="width:320px">
        <div class="card" style="padding:14px">
          <h4 style="margin:0 0 8px">Quick suggestions</h4>
          <div class="quick">
            <div class="chip">How to apply</div>
            <div class="chip">Fees & scholarships</div>
            <div class="chip">Campus tour</div>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
const chat = document.getElementById('chat');
const input = document.getElementById('input');
const send = document.getElementById('send');

function formatTime(d){
  const dt = new Date(d);
  return dt.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
}

function createMessage(text, who, ts){
  const wrapper = document.createElement('div');
  wrapper.className = 'msg ' + who;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  const meta = document.createElement('div');
  meta.style.fontSize='11px'; meta.style.marginTop='6px'; meta.style.color='var(--muted)';
  meta.textContent = formatTime(ts || Date.now());
  wrapper.appendChild(bubble);
  wrapper.appendChild(meta);
  return wrapper;
}

function showTyping(){
  const el = document.createElement('div');
  el.className = 'msg bot typing';
  el.id = 'typing-indicator';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = '<span style="display:inline-block;width:24px">&bull;&nbsp;</span>Typing...';
  el.appendChild(bubble);
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

function hideTyping(){
  const t = document.getElementById('typing-indicator');
  if(t) t.remove();
}

function appendMessage(text, who, ts){
  hideTyping();
  const el = createMessage(text, who, ts || Date.now());
  chat.appendChild(el);
  chat.scrollTop = chat.scrollHeight;
}

async function sendMessage(){
  const text = input.value.trim();
  if(!text) return;
  appendMessage(text, 'user');
  input.value = '';
  showTyping();
  try{
    const res = await fetch('/message', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text})});
    const data = await res.json();
    // small delay for UX
    setTimeout(()=>{ appendMessage(data.reply, 'bot'); }, 350);
  }catch(e){
    hideTyping();
    appendMessage('Unable to reach server. Please try again later.', 'bot');
  }
}

send.addEventListener('click', sendMessage);
input.addEventListener('keydown', (e)=>{ if(e.key==='Enter') sendMessage(); });

// quick chips
document.querySelectorAll('.chip').forEach(c=>c.addEventListener('click', ()=>{ input.value=c.textContent; sendMessage(); }));

// welcome message
appendMessage('Hello! I can help with courses, admissions, fees and campus visits. What would you like to know?', 'bot');
</script>
</body>
</html>
"""
INDEX_HTML = INDEX_HTML.replace('__BRAND_COLOR__', BRAND_COLOR)


@app.route('/')
def index():
    return render_template_string(INDEX_HTML)


@app.route('/message', methods=['POST'])
def message():
    data = request.get_json() or {}
    text = data.get('message', '')
    reply = find_faq_reply(text)
    if not reply:
        reply = DEFAULT_REPLY
    return jsonify({'reply': reply})


LOGIN_HTML = r"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Login</title>
<style>
  :root{--accent:__BRAND_COLOR__}
  body{font-family:Inter,system-ui,Segoe UI,Roboto,Arial;background:#f6f8fb;padding:20px;color:#0f172a}
  .card{max-width:420px;margin:40px auto;background:#fff;padding:24px;border-radius:10px;box-shadow:0 8px 20px rgba(2,6,23,0.06)}
  h3{margin-top:0;color:var(--accent)}
  input{width:100%;padding:10px;border:1px solid #e6eef8;border-radius:8px;box-sizing:border-box}
  button{background:var(--accent);color:#fff;padding:10px 16px;border-radius:8px;border:none;cursor:pointer;width:100%}
</style>
</head>
<body>
<div class="card">
<h3>Admin Login</h3>
{% if error %}<div style="color:#dc2626;margin-bottom:12px">{{ error }}</div>{% endif %}
<form method="post" action="/login">
  <div style="margin:12px 0"><input name="username" placeholder="Username" autocomplete="username" /></div>
  <div style="margin:12px 0"><input name="password" type="password" placeholder="Password" autocomplete="current-password" /></div>
  <div><button type="submit">Login</button></div>
</form>
</div>
</body>
</html>
"""
LOGIN_HTML = LOGIN_HTML.replace('__BRAND_COLOR__', BRAND_COLOR)


ADMIN_HTML = r"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Admin - FAQs</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
  <style>
    :root{--accent:__BRAND_COLOR__}
    body{font-family:Inter,system-ui,Segoe UI,Roboto,Arial;margin:0;background:#f6f8fb;color:#0f172a}
    .wrap{max-width:900px;margin:30px auto;padding:20px}
    .card{background:#fff;padding:24px;border-radius:10px;box-shadow:0 8px 20px rgba(2,6,23,0.06)}
    h2{margin:0 0 12px;color:var(--accent)}
    form>div{margin-bottom:12px}
    input[type=text], textarea{width:100%;padding:10px;border:1px solid #e6eef8;border-radius:8px;box-sizing:border-box}
    button{background:var(--accent);color:#fff;padding:10px 16px;border-radius:8px;border:none;cursor:pointer}
    table{width:100%;border-collapse:collapse;margin-top:14px}
    th,td{padding:10px;border-bottom:1px solid #f1f5f9;text-align:left}
    .muted{font-size:13px;color:#6b7280}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h2>FAQ Admin</h2>
      <p class="muted">Add a question and answer to the bot. You must be logged in to view this page.</p>
      <div style="display:flex;justify-content:flex-end;margin-bottom:10px"><a href="/logout" style="color:var(--accent)">Logout</a></div>
      <form method="post" action="/admin">
        <div>
          <label>Question</label>
          <input name="question" type="text" required />
        </div>
        <div>
          <label>Answer</label>
          <textarea name="answer" rows="4" required></textarea>
        </div>
        <div>
          <label>Keywords (comma-separated)</label>
          <input name="keywords" type="text" />
        </div>
        <div><button type="submit">Add FAQ</button></div>
      </form>

      <h3 style="margin-top:24px">Existing FAQs</h3>
      <table>
        <thead><tr><th>Question</th><th>Answer</th><th>Keywords</th></tr></thead>
        <tbody>
        {% for f in faqs %}
          <tr>
            <td>{{ f.question }}</td>
            <td>{{ f.answer }}</td>
            <td>{{ (f.keywords or []) | join(', ') }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""
ADMIN_HTML = ADMIN_HTML.replace('__BRAND_COLOR__', BRAND_COLOR)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # require login
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        q = request.form.get('question', '').strip()
        a = request.form.get('answer', '').strip()
        kws = request.form.get('keywords', '').strip()
        if q and a:
            new = {
                'id': max((f.get('id', 0) for f in FAQS), default=0) + 1,
                'question': q,
                'answer': a,
                'keywords': [k.strip() for k in kws.split(',') if k.strip()],
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            FAQS.append(new)
            save_faqs()
        return redirect(url_for('admin'))
    return render_template_string(ADMIN_HTML, faqs=FAQS)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        u = request.form.get('username', '')
        p = request.form.get('password', '')
        if u == ADMIN_USER and p == ADMIN_PASS:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        error = 'Invalid credentials'
    return render_template_string(LOGIN_HTML, error=error)


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


@app.route('/faqs', methods=['GET'])
def faqs():
    return jsonify(FAQS)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    try:
        from waitress import serve
        print("\n" + "="*60)
        print(f" PRC College Enquiry Chatbot Server is Live on port {port}!")
        print("="*60 + "\n")
        serve(app, host='0.0.0.0', port=port)
    except ImportError:
        app.run(host='0.0.0.0', port=port, debug=True)
