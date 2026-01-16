from flask import Flask, request, jsonify, session, redirect, render_template
from db import create_user, check_password, get_text, create_tables
import json
import os
from api import get_answer

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == 'POST':
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        domain = request.form.get("domain", "").strip()
        text = request.form.get("text", "").strip()

        if not username or not password:
            return "Missing username or password", 400
        
        create_user(username, password, domain, text)

        return redirect('/login')
    else:
        return render_template("register.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        print(username)
        id = check_password(username, password)
        print(id)
        if id:
            session["user_id"] = id
            return redirect("/")

        return "Invalid credentials", 401


    return render_template("login.html")

@app.route("/", methods=["GET"])    
def index():
    if "user_id" not in session:
        return redirect("/login")
    return redirect("/ask")
    text = get_text(session['user_id'])
    return render_template('index.html', text=text)

@app.route("/ask", methods=["GET"])
def ask():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("widget.html")

@app.route("/ask_question", methods=["POST"])
def ask_question():
    if "user_id" not in session:
        return redirect("/login")

    data = request.json
    question = data.get("question")
    user_id = session['user_id']
    answer = get_answer(question, user_id)
    if not question:
        return jsonify({"error": "No question provided"}), 400
    return jsonify({"answer": answer})

    
if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
