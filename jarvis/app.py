# ==========================================================
# J.A.R.V.I.S â€“ PROFESSIONAL KALI CONTROL PLATFORM
# Version: 2.0 (Clean, Stable, No LLM, No Voice)
# Authoritative Web UI â€¢ Full Kali Command Control
# ==========================================================

import os
import subprocess
import threading
from flask import Flask, request, redirect, session, jsonify, send_file, render_template_string
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename

# ---------------- CONFIG ----------------
HOST = "0.0.0.0"
PORT = 8000
SECRET_KEY = "jarvis-enterprise-key"
UPLOAD_DIR = "/tmp/jarvis_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

USERS = {
    "admin": {"password": "kali", "role": "root"},
    "user": {"password": "user", "role": "user"}
}

TOOL_PRESETS = {
    "WiFi": ["airmon-ng", "airodump-ng", "aireplay-ng"],
    "OSINT": ["theHarvester", "amass", "recon-ng"],
    "Exploitation": ["msfconsole", "searchsploit"],
    "System": ["htop", "ip a", "ss -tulpn"]
}

# ---------------- APP ----------------
app = Flask(__name__)
app.secret_key = SECRET_KEY
socketio = SocketIO(app, async_mode="threading")

# ---------------- AUTH ----------------
def login_required(role=None):
    def wrapper(fn):
        def decorated(*args, **kwargs):
            if "user" not in session:
                return redirect("/login")
            if role and session.get("role") != role:
                return "Access denied", 403
            return fn(*args, **kwargs)
        decorated.__name__ = fn.__name__
        return decorated
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if u in USERS and USERS[u]["password"] == p:
            session["user"] = u
            session["role"] = USERS[u]["role"]
            return redirect("/")
        return render_template_string(LOGIN_HTML, error="Invalid credentials")
    return render_template_string(LOGIN_HTML)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- DASHBOARD ----------------
@app.route("/")
@login_required()
def index():
    return render_template_string(DASHBOARD_HTML, presets=TOOL_PRESETS, user=session['user'], role=session['role'])

# ---------------- TERMINAL ----------------
@socketio.on("run")
def run_cmd(data):
    cmd = data.get("cmd")
    if not cmd:
        return
    def task():
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in process.stdout:
            socketio.emit("output", line)
    threading.Thread(target=task).start()

# ---------------- FILES ----------------
@app.route("/files")
@login_required()
def files():
    path = request.args.get("path", "/")
    try:
        return jsonify(os.listdir(path))
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/upload", methods=["POST"])
@login_required("root")
def upload():
    f = request.files['file']
    name = secure_filename(f.filename)
    dest = os.path.join(UPLOAD_DIR, name)
    f.save(dest)
    return "Uploaded"

@app.route("/download")
@login_required()
def download():
    return send_file(request.args.get("path"), as_attachment=True)

# ---------------- PROCESSES ----------------
@app.route("/processes")
@login_required()
def processes():
    return jsonify(os.popen("ps aux").read().splitlines())

# ---------------- UI ----------------
LOGIN_HTML = """
<!doctype html><html><head><style>
body{background:#0e1117;color:#c9d1d9;font-family:Inter,Arial}
.card{width:320px;margin:10% auto;padding:30px;background:#161b22;border-radius:12px}
input,button{width:100%;margin:8px 0;padding:10px;border-radius:8px;border:none}
button{background:#238636;color:white;font-weight:bold}
</style></head><body>
<div class='card'>
<h2>J.A.R.V.I.S Login</h2>
{% if error %}<p style='color:red'>{{error}}</p>{% endif %}
<form method='post'>
<input name='username' placeholder='Username'>
<input name='password' type='password' placeholder='Password'>
<button>Access System</button>
</form></div></body></html>
"""

DASHBOARD_HTML = """
<!doctype html><html><head>
<script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
<style>
body{margin:0;background:#0e1117;color:#00ffcc;font-family:Inter,Arial}
header{padding:15px;background:#161b22;display:flex;justify-content:space-between}
main{display:grid;grid-template-columns:260px 1fr;height:90vh}
nav{background:#161b22;padding:15px;overflow:auto}
section{padding:15px}
button{background:#21262d;color:#c9d1d9;border:none;padding:8px;margin:4px;border-radius:6px}
button:hover{background:#30363d}
#term{background:black;height:100%;padding:10px;overflow:auto;font-family:monospace}
input{width:100%;padding:8px;border-radius:6px;border:none;margin-top:5px}
</style></head><body>
<header><b>J.A.R.V.I.S</b><span>{{user}} ({{role}}) | <a href='/logout' style='color:#00ffcc'>Logout</a></span></header>
<main>
<nav>
<h4>Tool Presets</h4>
{% for k,v in presets.items() %}
<b>{{k}}</b><br>
{% for t in v %}<button onclick="run('{{t}}')">{{t}}</button>{% endfor %}<br><br>
{% endfor %}
</nav>
<section>
<div id='term'></div>
<input id='cmd' placeholder='Enter Kali command and press Enter'>
</section>
</main>
<script>
const s=io();
cmd.onkeydown=e=>{if(e.key==='Enter'){run(cmd.value);cmd.value='';}};
function run(c){s.emit('run',{cmd:c});}
s.on('output',d=>{term.innerHTML+=d+'<br>';term.scrollTop=999999;});
</script></body></html>
"""

# ---------------- MAIN ----------------
if __name__ == '__main__':
    socketio.run(app, host=HOST, port=PORT)
