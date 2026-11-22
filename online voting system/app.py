from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3, os, hashlib, secrets, random, smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

DB = os.path.join(os.path.dirname(__file__), "voting.db")

# ── Email Config (update these!) ──────────────────────────────────────────────
EMAIL_ADDRESS  = "anbalaganabinaya852@gmail.com"
EMAIL_PASSWORD = "rmjp howt jele fhvp"

# ── DB Setup ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                password TEXT    NOT NULL,
                email    TEXT,
                is_admin INTEGER DEFAULT 0,
                voted    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS candidates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                party       TEXT,
                description TEXT,
                votes       INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                username   TEXT NOT NULL,
                action     TEXT NOT NULL,
                timestamp  TEXT NOT NULL
            );
        """)
        pw = hashlib.sha256("admin123".encode()).hexdigest()
        try:
            db.execute("INSERT INTO users (username,password,is_admin) VALUES (?,?,1)",
                       ("admin", pw))
            db.commit()
        except sqlite3.IntegrityError:
            pass

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def log_action(username, action):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as db:
        db.execute("INSERT INTO audit_log (username, action, timestamp) VALUES (?,?,?)",
                   (username, action, ts))
        db.commit()

# ── OTP ───────────────────────────────────────────────────────────────────────
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(to_email, otp):
    try:
        msg = MIMEText(f"Your VoteNow OTP is: {otp}\n\nValid for 10 minutes. Do not share this.")
        msg["Subject"] = "VoteNow — Your OTP Code"
        msg["From"]    = EMAIL_ADDRESS
        msg["To"]      = to_email
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("vote"))
    if request.method == "POST":
        uname = request.form["username"].strip()
        pw    = hash_pw(request.form["password"])
        print("USERNAME:", uname)
        print("PASSWORD HASH:", pw)
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                              (uname, pw)).fetchone()
        if user:
            if user["email"] and not user["is_admin"]:
                otp = generate_otp()
                session["pending_user_id"]  = user["id"]
                session["pending_username"] = user["username"]
                session["pending_is_admin"] = user["is_admin"]
                session["pending_voted"]    = user["voted"]
                session["otp"]              = otp
                sent = send_otp_email(user["email"], otp)
                flash("OTP sent to your email!" if sent else "Could not send OTP. Check email config.")
                return redirect(url_for("verify_otp"))
            else:
                session["user_id"]  = user["id"]
                session["username"] = user["username"]
                session["is_admin"] = user["is_admin"]
                session["voted"]    = user["voted"]
                log_action(user["username"], "Logged in")
                return redirect(url_for("admin_panel") if user["is_admin"] else url_for("vote"))
        flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/verify-otp", methods=["GET","POST"])
def verify_otp():
    if "pending_user_id" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        entered = request.form.get("otp", "").strip()
        if entered == session.get("otp"):
            session["user_id"]  = session.pop("pending_user_id")
            session["username"] = session.pop("pending_username")
            session["is_admin"] = session.pop("pending_is_admin")
            session["voted"]    = session.pop("pending_voted")
            session.pop("otp", None)
            log_action(session["username"], "Logged in with OTP")
            return redirect(url_for("vote"))
        flash("Incorrect OTP. Please try again.")
    return render_template("verify_otp.html")

@app.route("/resend-otp")
def resend_otp():
    if "pending_user_id" not in session:
        return redirect(url_for("login"))
    with get_db() as db:
        user = db.execute("SELECT email FROM users WHERE id=?",
                          (session["pending_user_id"],)).fetchone()
    if user and user["email"]:
        otp = generate_otp()
        session["otp"] = otp
        send_otp_email(user["email"], otp)
        flash("A new OTP has been sent to your email.")
    return redirect(url_for("verify_otp"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        uname = request.form["username"].strip()
        pw    = hash_pw(request.form["password"])
        email = request.form.get("email", "").strip()
        try:
            with get_db() as db:
                db.execute("INSERT INTO users (username,password,email) VALUES (?,?,?)",
                           (uname, pw, email))
                db.commit()
            log_action(uname, "Registered")
            flash("Account created! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already taken.")
    return render_template("register.html")

@app.route("/logout")
def logout():
    username = session.get("username", "unknown")
    log_action(username, "Logged out")
    session.clear()
    return redirect(url_for("login"))

# ── Voting ────────────────────────────────────────────────────────────────────
@app.route("/vote", methods=["GET","POST"])
def vote():
    if "user_id" not in session:
        return redirect(url_for("login"))
    if session.get("is_admin"):
        return redirect(url_for("admin_panel"))
    with get_db() as db:
        candidates = db.execute("SELECT * FROM candidates").fetchall()
    if request.method == "POST":
        if session.get("voted"):
            flash("You have already voted!")
            return redirect(url_for("results"))
        cid = request.form.get("candidate_id")
        if cid:
            with get_db() as db:
                cand = db.execute("SELECT name FROM candidates WHERE id=?", (cid,)).fetchone()
                db.execute("UPDATE candidates SET votes=votes+1 WHERE id=?", (cid,))
                db.execute("UPDATE users SET voted=1 WHERE id=?", (session["user_id"],))
                db.commit()
            session["voted"] = 1
            log_action(session["username"], f"Voted for: {cand['name']}")
            flash("Your vote has been cast!")
            return redirect(url_for("results"))
        flash("Please select a candidate.")
    return render_template("vote.html", candidates=candidates,
                           already_voted=session.get("voted", 0))

# ── Results ───────────────────────────────────────────────────────────────────
@app.route("/results")
def results():
    if "user_id" not in session:
        return redirect(url_for("login"))
    with get_db() as db:
        candidates = db.execute("SELECT * FROM candidates ORDER BY votes DESC").fetchall()
        total = db.execute("SELECT SUM(votes) as t FROM candidates").fetchone()["t"] or 0
    return render_template("results.html", candidates=candidates, total=total)

@app.route("/results/data")
def results_data():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401
    with get_db() as db:
        candidates = db.execute(
            "SELECT name, party, votes FROM candidates ORDER BY votes DESC").fetchall()
        total = db.execute("SELECT SUM(votes) as t FROM candidates").fetchone()["t"] or 0
    return jsonify({
        "total": total,
        "candidates": [{"name": c["name"], "party": c["party"], "votes": c["votes"]} for c in candidates]
    })

# ── Admin ─────────────────────────────────────────────────────────────────────
@app.route("/admin", methods=["GET","POST"])
def admin_panel():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            name  = request.form["name"].strip()
            party = request.form["party"].strip()
            desc  = request.form["description"].strip()
            if name:
                with get_db() as db:
                    db.execute("INSERT INTO candidates (name,party,description) VALUES (?,?,?)",
                               (name, party, desc))
                    db.commit()
                log_action("admin", f"Added candidate: {name}")
                flash(f"Candidate '{name}' added!")
        elif action == "delete":
            cid = request.form.get("candidate_id")
            with get_db() as db:
                cand = db.execute("SELECT name FROM candidates WHERE id=?", (cid,)).fetchone()
                db.execute("DELETE FROM candidates WHERE id=?", (cid,))
                db.commit()
            log_action("admin", f"Deleted candidate: {cand['name']}")
            flash("Candidate removed.")
        elif action == "reset":
            with get_db() as db:
                db.execute("UPDATE candidates SET votes=0")
                db.execute("UPDATE users SET voted=0")
                db.commit()
            log_action("admin", "Reset all votes")
            flash("All votes have been reset.")
    with get_db() as db:
        candidates = db.execute("SELECT * FROM candidates ORDER BY id").fetchall()
        users      = db.execute("SELECT * FROM users WHERE is_admin=0").fetchall()
        logs       = db.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 50").fetchall()
    return render_template("admin.html", candidates=candidates, users=users, logs=logs)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)

