from flask import Flask, request, jsonify, session, redirect, render_template, make_response, abort
from db_pool import Database
import json
import os
from api import get_answer
import content
import secrets


with open("resources/config.json") as f:
    config = json.load(f)

db = Database(config)

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
            return "Missing username or password", 400
        db.create_user(username, password)
        return redirect('/login')
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
            return redirect("/")
        return {"error" : "Invalid Credentials"}, 401
    return render_template("login.html")

@app.route("/", methods=["GET"])
def index():
    """Return an index page"""
    if "user_id" not in session:
        return redirect("/login")
    data = db.get_data(session['user_id'])
    return render_template('index.html', domains=data)

@app.route("/ask", methods=["GET"])
def ask():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("widget.html")

@app.route("/create", methods=["POST"])
def create():
    if "user_id" not in session:
        return {"status" : "Invalid Credentials"}, 403
    domain = request.form["domain"]
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
    try:
        answer = get_answer(question, token, db)
    except Exception as e:
        print(e)
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
    return render_template('edit.html', sources=data, token=token, fallback_msg=fallback_msg)


@app.route("/edit/update/<token>", methods=["POST"])
def update_text(token):
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    json_data = request.json
    if not db.check_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    new_text = json_data.get('data')
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

@app.route("/edit/fallback/update/<token>", methods=["POST"])
def update_fallback(token):
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    json_data = request.json
    if not db.check_data_token(session['user_id'], token):
        return {"error" : "Invalid Credentials"}, 403
    new_text = json_data.get('data')
    db.update_fallback(token, new_text)
    return {}, 200

@app.route("/api/scarp" ,methods=["POST"])
def scarp_page():
    if "user_id" not in session:
        return {"error" : "Invalid Credentials"}, 403
    url = request.json.get("url")
    depth = min(2, max(0, int(request.json.get("depth", 0))))
    try:
        pages = content.crawl(url, max_depth=depth)
        text = "\n\n".join(pages)
    except Exception as e:
        return {"text" : ""}, 400
    return {"text" : text}, 200

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")
    

if __name__ == "__main__":
    db.create_tables()
    app.run(debug=True)
