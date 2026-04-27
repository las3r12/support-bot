from flask import Flask, request, jsonify, session, redirect, render_template, make_response, abort
from db_pool import Database
from api import LLMClient
from functools import wraps
from dotenv import load_dotenv
import json
import os
import content
import secrets
from content import Scraper
from rate_limit import IPRateLimiter
from datetime import timedelta

load_dotenv()

with open("resources/config.json") as f:
    config = json.load(f)

config['db_name'] = os.environ['DB_NAME']
config['db_user'] = os.environ['DB_USER']
config['db_password'] = os.environ['DB_PASSWORD']

db = Database(config, retrieval_distance_threshold=config['retrieval_distance_threshold'], retrieval_top_k=config['retrieval_top_k'])
scarper = Scraper(timeout=config['scraper_timeout'], max_page_bytes=config['max_scrape_page_bytes'])
llm = LLMClient(os.environ['LLM_KEY'], config['max_context_len'], config['model'])
rate_limiter = IPRateLimiter(config["rate_limit_per_ip"], config["rate_limit_window_sec"])
widget_rate_limiter = IPRateLimiter(config["rate_limit_widget_per_ip"], config["rate_limit_widget_window_sec"])
app = Flask(__name__)

app.secret_key = os.environ['SECRET_KEY']
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=config["session_lifetime_hours"])
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or db.get_role(session['user_id']) is None:
            session.clear()
            if request.method == 'GET':
                return redirect("/login")
            return {"error": "Invalid Credentials"}, 403
        return f(*args, **kwargs)
    return decorated


@app.errorhandler(413)
def request_too_large(_):
    return jsonify({"error": f"Content is too large (max {config['max_source_len']} characters)"}), 413

@app.errorhandler(403)
def forbidden(_):
    if request.method == 'GET':
        return render_template("403.html"), 403
    return jsonify({"error": "Forbidden"}), 403

@app.before_request
def check_rate_limit():
    if request.method == "OPTIONS" or request.path.startswith("/static/"):
        return
    if request.path in ("/ask_question", "/api/scarp/links", "/api/scarp/fetch"):
        limiter = widget_rate_limiter
    elif "user_id" in session or request.path in ("/login", "/register"):
        limiter = rate_limiter
    else:
        return
    if not limiter.is_allowed(request.remote_addr):
        resp = jsonify({"error": f"Too many requests. Next request possible in {limiter.next_allowed(request.remote_addr)}s"})
        if request.path == "/ask_question":
            resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp, 429


def validate_password(password: str):
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if len(password) > 100:
        return "Password must be 100 characters or less"
    if not any(c.isupper() for c in password):
        return "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one number"
    return None


@app.context_processor
def inject_is_admin():
    if 'user_id' in session:
        return {'is_admin': db.get_role(session['user_id']) == 'admin'}
    return {'is_admin': False}


@app.before_request
def check_csrf():
    if 'user_id' not in session:
        return
    if request.method in ('POST'):
        if request.is_json:
            token = request.headers.get('X-CSRF-Token')
        else:
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if token != session.get('csrf_token'):
            abort(403)


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            return jsonify({"error" : "Missing username or password"}), 400
        if len(username) < 8:
            return jsonify({"error": "Username must be at least 8 characters"}), 400
        if len(username) > 100:
            return jsonify({"error": "Username must be 100 characters or less"}), 400
        if not username.isprintable() or any(c.isspace() for c in username):
            return jsonify({"error": "Username must not contain spaces or whitespace"}), 400
        if db.user_exists(username):
            return jsonify({"error" : "Username already taken"}), 400
        pw_error = validate_password(password)
        if pw_error:
            return jsonify({"error": pw_error}), 400
        db.create_user(username, password)
        return {}, 200
    else:
        return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        id = db.check_password(username, password)
        if id:
            session["user_id"] = id
            session['csrf_token'] = secrets.token_hex(32)
            return {}, 200
        return {"error" : "Invalid Credentials"}, 401
    return render_template("login.html")

@app.route("/", methods=["GET"])
@login_required
def index():
    data = db.get_data(session['user_id'])
    return render_template('index.html', domains=data)

@app.route("/create", methods=["POST"])
@login_required
def create():
    domain = request.form.get("domain", "").strip()
    if not domain:
        return {"error": "Domain can't be empty"}, 400
    if len(domain) > config['max_domain_length']:
        return {"error": f"Domain must be {config['max_domain_length']} characters or less"}, 400
    if len(db.get_data(session['user_id'])) >= config['max_domains_per_account']:
        return {"error": f"Maximum of {config['max_domains_per_account']} domains per account"}, 400
    result = db.add_website(domain, session['user_id'])
    if result is False:
        return {"error": "You already have a bot for this domain"}, 400
    if result is None:
        return {"error": "Failed to create domain"}, 500
    return redirect("/")

@app.route("/edit/<token>/add", methods=["POST"])
@login_required
def add_data_source(token):
    if not db.check_data_token(session['user_id'], token):
        return {"status" : "Invalid Credentials"}, 403
    name = request.json.get("name", "")
    text = request.json.get("text", "")
    if not name or name == "":
        return {"error" : "Source name can't be empty"}, 400
    if len(name) > 200:
        return {"error": "Source name must be 200 characters or less"}, 400
    if not text or text == "":
        return {"error" : "Source text can't be empty"}, 400
    if len(text) > config["max_source_len"]:
        return {"error": f"Source text must be {config['max_source_len']} characters or less"}, 400
    if db.count_sources(token) >= config["max_sources_per_bot"]:
        return {"error": f"Maximum of {config['max_sources_per_bot']} data sources per bot"}, 400
    if db.add_source(token, name, text) is False:
        return {"error": "A source with this name already exists"}, 400
    return redirect("/edit/"+token)


@app.route("/edit/<token>/delete", methods=["POST"])
@login_required
def remove_data_source(token):
    if not db.check_data_token(session['user_id'], token):
        return {"status" : "Invalid Credentials"}, 403
    db.remove_website(token)
    return {}, 200


@app.route("/ask_question", methods=["OPTIONS"])
def ask_question_options():
    response = make_response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

@app.route("/ask_question", methods=["POST"])
def ask_question():
    data = request.json
    question = data.get("question")
    if not question:
        resp = jsonify({"error": "No question provided"})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp, 400
    if len(question) > config["max_question_len"]:
        resp = jsonify({"error": "Question too long"})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp, 400
    token = data.get("token")
    if not db.get_bot_enabled(token):
        resp = jsonify({"answer": "This bot is currently disabled."})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
    if db.get_credits(token) <= 0:
        resp = jsonify({"answer": config["no_credits_msg"]})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
    history = str(data.get('history', ''))[:config["max_history_len"]]
    try:
        answer = llm.get_answer(question, history, token, db)
    except Exception as e:
        print(e)
    db.deduct_credit(token)
    if (answer['status'] == 'fallback'):
        answer = db.get_fallback(token)
    else:
        answer = answer['response']
    data = jsonify({"answer": answer})
    response = make_response(data)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route("/edit/<token>", methods=["GET"])
@login_required
def send_edit_page(token):
    if not db.check_data_token(session['user_id'], token):
        return redirect("/")
    data = db.get_all_texts(token)
    fallback_msg = db.get_fallback(token)[0]
    bot_name = db.get_bot_name(token)
    bot_enabled = db.get_bot_enabled(token)
    hello_msg = db.get_hello_msg(token)
    return render_template('edit.html', sources=data, token=token, fallback_msg=fallback_msg, bot_name=bot_name, bot_enabled=bot_enabled, hello_msg=hello_msg, max_source_len=config['max_source_len'], max_scrape_depth=config['max_scrape_depth'])


@app.route("/edit/update/<token>", methods=["POST"])
@login_required
def update_text(token):
    json_data = request.json
    if not db.check_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    new_text = json_data.get('data')
    if not new_text or new_text == "":
        return {"error" : "Source text can't be empty"}, 400
    if len(new_text) > config["max_source_len"]:
        return {"error": f"Source text must be {config['max_source_len']} characters or less"}, 400
    db.update_text(token, new_text)
    return {}, 200

@app.route("/edit/delete/<token>", methods=["POST"])
@login_required
def delete_text(token):
    if not db.check_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    db.remove_text(token)
    return {}, 200

@app.route("/bot_info/<token>", methods=["GET"])
def bot_info(token):
    name = db.get_bot_name(token)
    hello_msg = db.get_hello_msg(token)
    response = make_response(jsonify({"bot_name": name, "hello_msg": hello_msg}))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route("/edit/<token>/name/update", methods=["POST"])
@login_required
def update_bot_name(token):
    if not db.check_data_token(session['user_id'], token):
        return {"error": "Invalid Credentials"}, 403
    name = request.json.get("data", "").strip()
    if not name:
        return {"error": "Bot name can't be empty"}, 400
    if len(name) > config['max_bot_name_length']:
        return {"error": f"Bot name must be {config['max_bot_name_length']} characters or less"}, 400
    db.update_bot_name(token, name)
    return {}, 200

@app.route("/edit/<token>/enabled/update", methods=["POST"])
@login_required
def update_bot_enabled(token):
    if not db.check_data_token(session['user_id'], token):
        return {"error": "Invalid Credentials"}, 403
    enabled = request.json.get("enabled")
    if not isinstance(enabled, bool):
        return {"error": "Invalid value"}, 400
    db.set_bot_enabled(token, enabled)
    return {}, 200

@app.route("/edit/<token>/hello/update", methods=["POST"])
@login_required
def update_hello_msg(token):
    if not db.check_data_token(session['user_id'], token):
        return {"error": "Invalid Credentials"}, 403
    msg = request.json.get("data", "").strip()
    if not msg:
        return {"error": "Hello message can't be empty"}, 400
    if len(msg) > config["max_hello_msg_len"]:
        return {"error": f"Hello message must be {config['max_hello_msg_len']} characters or less"}, 400
    db.update_hello_msg(token, msg)
    return {}, 200

@app.route("/edit/<token>/fallback/update", methods=["POST"])
@login_required
def update_fallback(token):
    json_data = request.json
    if not db.check_data_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    new_text = json_data.get('data')
    if new_text == "":
        return {"error" : "Can't set an empty message"}, 400
    db.update_fallback(token, new_text)
    return {}, 200

@app.route("/api/scarp/links", methods=["POST"])
@login_required
def scarp_links():
    url = request.json.get("url")
    if not url:
        return {"error": "No URL provided"}, 400
    depth = min(config["max_scrape_depth"], max(0, int(request.json.get("depth", 0))))
    try:
        links = scarper.get_links(url, max_links=config["max_scrape_links"], max_depth=depth)
    except Exception as e:
        return {"error": str(e)}, 400
    return {"links": links, "max_select": config["max_scrape_select"]}, 200

@app.route("/api/scarp/fetch", methods=["POST"])
@login_required
def scarp_fetch():
    urls = request.json.get("urls", [])
    if not isinstance(urls, list) or not urls:
        return {"error": "No URLs provided"}, 400
    if len(urls) > config["max_scrape_select"]:
        return {"error": f"Maximum {config['max_scrape_select']} URLs allowed"}, 400
    for url in urls:
        if not isinstance(url, str):
            return {"error": "Invalid URL list"}, 400
    try:
        text = scarper.fetch_pages(urls)
    except Exception as e:
        return {"error": str(e)}, 400
    return {"text": text}, 200

@app.route("/account", methods=["GET"])
@login_required
def account():
    credits = db.get_credits_by_user(session["user_id"])
    username = db.get_username(session["user_id"])
    return render_template("account.html", credits=credits, username=username)

@app.route("/account/password", methods=["POST"])
@login_required
def change_password():
    json_data = request.json
    old_pw = json_data.get("old_password", "")
    new_pw = json_data.get("new_password", "")
    pw_error = validate_password(new_pw)
    if pw_error:
        return {"error": pw_error}, 400
    if not db.change_password(session["user_id"], old_pw, new_pw):
        return {"error": "Current password is incorrect"}, 400
    return {}, 200

@app.route("/admin", methods=["GET"])
@login_required
def admin():
    if db.get_role(session["user_id"]) != "admin":
        abort(403)
    users = db.get_users()
    return render_template("admin.html", users=users)

@app.route("/admin/credits/<int:user_id>", methods=["POST"])
@login_required
def update_credits(user_id):
    if db.get_role(session["user_id"]) != "admin":
        abort(403)
    json_data = request.json
    credits = json_data.get("credits")
    if credits is None or not isinstance(credits, int) or credits < 0:
        return {"error": "Invalid credits value"}, 400
    db.set_credits(user_id, credits)
    return {}, 200

@app.route("/admin/disable/<int:user_id>", methods=["POST"])
@login_required
def disable_user(user_id):
    if db.get_role(session["user_id"]) != "admin":
        abort(403)
    if not db.disable_user(user_id):
        return {"error": "User not found"}, 404
    return {}, 200

@app.route("/admin/enable/<int:user_id>", methods=["POST"])
@login_required
def enable_user(user_id):
    if db.get_role(session["user_id"]) != "admin":
        abort(403)
    if not db.enable_user(user_id):
        return {"error": "User not found"}, 404
    return {}, 200

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
    
if __name__ == "__main__":
    db.create_tables()
    ssl = ('keys/localhost.pem', 'keys/localhost-key.pem')
    app.run(debug=True, ssl_context=ssl)
