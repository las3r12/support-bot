from flask import Flask, request, jsonify, session, redirect, render_template, make_response, abort
from db_pool import Database
from api import LLMClient
import json
import os
import content
import secrets
from content import Scarper


with open("resources/config.json") as f:
    config = json.load(f)

db = Database(config)
scarper = Scarper()
llm = LLMClient(config['llm_key'], config['max_context_len'])
app = Flask(__name__)
#app.secret_key = os.urandom(24)
app.secret_key = 'g'


@app.before_request
def check_csrf():
    if 'user_id' not in session:
        return
    if request.method in ('POST'):
        token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        if token != session.get('csrf_token'):
            abort(403)


@app.route("/register", methods=["POST", "GET"])
def register():
    """Register a new user on the website."""
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if not username or not password:
            return jsonify({"error" : "Missing username or password"}), 400
        if db.user_exists(username):
            return jsonify({"error" : "Username already taken"}), 400
        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters"}), 400
        db.create_user(username, password)
        return {}, 200
    else:
        return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    """Log in into an existing account."""
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
def index():
    """Return an index page"""
    if "user_id" not in session:
        return redirect("/login")
    data = db.get_data(session['user_id'])
    return render_template('index.html', domains=data)

@app.route("/create", methods=["POST"])
def create():
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    domain = request.form["domain"]
    if not domain or domain == "":
        return {"error" : "Empty Domain"}, 400
    db.add_website(domain, session['user_id'])
    return redirect("/")

@app.route("/edit/<token>/add", methods=["POST"])
def add_data_source(token):
    if "user_id" not in session:
        return {"status" : "Invalid Credentials"}, 403
    if not db.check_data_token(session['user_id'], token):
        return {"status" : "Invalid Credentials"}, 403
    name = request.form["name"]
    text = request.form["text"]
    if not name or name == "":
        return {"error" : "Source name can't be empty"}, 400
    if not text or text == "":
        return {"error" : "Source text can't be empty"}, 400
    db.add_source(token, name, text)
    return redirect("/edit/"+token)


@app.route("/edit/<token>/delete", methods=["POST"])
def remove_data_source(token):
    if "user_id" not in session:
        return {"status" : "Invalid Credentials"}, 403
    if not db.check_data_token(session['user_id'], token):
        return {"status" : "Invalid Credentials"}, 403


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
        data = jsonify({"error": "No question provided"}), 400
    token = data.get("token")
    if db.get_credits(token) <= 0:
        resp = jsonify({"answer": config["no_credits_msg"]})
        resp.headers["Access-Control-Allow-Origin"] = "*"
        return resp
    try:
        answer = llm.get_answer(question, str(data.get('history')), token, db)
        print(answer)
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
def send_edit_page(token):
    if "user_id" not in session:
        return redirect("/login")
    if not db.check_data_token(session['user_id'], token):
        return redirect("/")
    data = db.get_all_texts(token)
    fallback_msg = db.get_fallback(token)[0]
    bot_name = db.get_bot_name(token)
    return render_template('edit.html', sources=data, token=token, fallback_msg=fallback_msg, bot_name=bot_name)


@app.route("/edit/update/<token>", methods=["POST"])
def update_text(token):
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    json_data = request.json
    if not db.check_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    new_text = json_data.get('data')
    if not new_text or new_text == "":
        return {"error" : "Source text can't be empty"}, 400
    db.update_text(token, new_text)
    return {}, 200

@app.route("/edit/delete/<token>", methods=["POST"])
def delete_text(token):
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    if not db.check_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    db.remove_text(token)
    return {}, 200

@app.route("/bot_info/<token>", methods=["GET"])
def bot_info(token):
    name = db.get_bot_name(token)
    response = make_response(jsonify({"bot_name": name}))
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.route("/edit/<token>/name/update", methods=["POST"])
def update_bot_name(token):
    if "user_id" not in session:
        return {"error": "Invalid Credentials"}, 403
    if not db.check_data_token(session['user_id'], token):
        return {"error": "Invalid Credentials"}, 403
    name = request.json.get("data", "").strip()
    if not name:
        return {"error": "Bot name can't be empty"}, 400
    db.update_bot_name(token, name)
    return {}, 200

@app.route("/edit/<token>/fallback/update", methods=["POST"])
def update_fallback(token):
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    json_data = request.json
    if not db.check_data_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    new_text = json_data.get('data')
    if new_text == "":
        return {"error" : "Can't set an empty message"}, 400
    db.update_fallback(token, new_text)
    return {}, 200

@app.route("/api/scarp" ,methods=["POST"])
def scarp_page():
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    url = request.json.get("url")
    depth = min(2, max(0, int(request.json.get("depth", 0))))
    try:
        pages = scarper.crawl(url, max_depth=depth)
        text = "\n\n".join(pages)
    except Exception as e:
        return {"text" : ""}, 400
    return {"text" : text}, 200

@app.route("/account", methods=["GET"])
def account():
    if "user_id" not in session:
        return redirect("/login")
    credits = db.get_credits_by_user(session["user_id"])
    return render_template("account.html", credits=credits)

@app.route("/account/password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return {"error": "Invalid Credentials"}, 403
    json_data = request.json
    old_pw = json_data.get("old_password", "")
    new_pw = json_data.get("new_password", "")
    if len(new_pw) < 8:
        return {"error": "Password must be at least 8 characters"}, 400
    if not db.change_password(session["user_id"], old_pw, new_pw):
        return {"error": "Current password is incorrect"}, 400
    return {}, 200

@app.route("/admin", methods=["GET"])
def admin():
    if "user_id" not in session:
        return redirect("/login")
    if db.get_role(session["user_id"]) != "admin":
        abort(403)
    users = db.get_users()
    return render_template("admin.html", users=users)

@app.route("/admin/credits/<int:user_id>", methods=["POST"])
def update_credits(user_id):
    if "user_id" not in session:
        return {"error": "Invalid Credentials"}, 403
    if db.get_role(session["user_id"]) != "admin":
        abort(403)
    json_data = request.json
    credits = json_data.get("credits")
    if credits is None or not isinstance(credits, int) or credits < 0:
        return {"error": "Invalid credits value"}, 400
    db.set_credits(user_id, credits)
    return {}, 200

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
    
if __name__ == "__main__":
    db.create_tables()
    app.run(debug=True)
