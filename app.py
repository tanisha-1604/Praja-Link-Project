from flask import Flask, request, jsonify, render_template
from flask import redirect, url_for, session
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import base64


app = Flask(__name__)
CORS(app)
app.secret_key = "your_secret_key_here"  # change to a secure secret in production 

# --- Home & Page Routes ---
@app.route("/")
def home():
    return render_template("admin.html")

@app.route("/services")
def services():
    # This opens the report submission form (citizen side)
    return render_template("report_form.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        dob = request.form.get("dob")
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        email = request.form.get("email")

        conn = sqlite3.connect("citizens.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO citizens (name, dob, age, gender, phone, email) VALUES (?, ?, ?, ?, ?, ?)",
            (name, dob, age, gender, phone, email),
        )
        conn.commit()
        conn.close()

        # After successful registration
        return render_template("report_redirect.html", message="Registration successful!")

    return render_template("register.html")


@app.route("/employee", methods=["GET", "POST"])
def employee():
    if request.method == "POST":
        name = request.form.get("citizen-name")
        emp_id = request.form.get("employee-id")
        password = request.form.get("password")
        profile_status = request.form.get("profile-status")
        phone = request.form.get("phone")
        email = request.form.get("email")

        # ✅ Simple example (you can later connect it to an employee DB)
        if emp_id == "123" and password == "admin":
            session["employee"] = name
            return redirect(url_for("employee_dashboard"))
        else:
            return render_template("Employee.html", error="Invalid ID or password!")

    return render_template("Employee.html")

@app.route("/employee/dashboard")
def employee_dashboard():
    if "employee" not in session:
        return redirect(url_for("employee"))  # Redirect if not logged in
    # Ensure DB and table exist to avoid runtime errors
    try:
        init_reports_db()
    except Exception as e:
        print("⚠️ init_reports_db failed:", e)

    try:
        conn = sqlite3.connect("reports.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports ORDER BY created_at DESC")
        reports = cursor.fetchall()
        conn.close()
        error_message = None
    except Exception as e:
        print("⚠️ Error loading reports:", e)
        reports = []
        error_message = "Could not load reports from the database."

    return render_template("employee_dashboard.html", reports=reports, error_message=error_message)


# --- Admin Status Board (for employees) ---
@app.route("/admin-dashboard")
def admin_dashboard():
    if "employee" not in session:
        return redirect(url_for("employee"))

    try:
        conn = sqlite3.connect("reports.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM reports ORDER BY created_at DESC")
        reports = cur.fetchall()
        conn.close()
    except Exception as e:
        print("⚠️ Error loading reports for admin dashboard:", e)
        reports = []

    return render_template("admin_dashboard.html", reports=reports)


@app.route("/update_status/<int:report_id>", methods=["POST"])
def update_status(report_id: int):
    if "employee" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        data = request.get_json(force=True)
        new_status = (data.get("status") or "").strip()
        # Map display values back to DB values
        # UI shows "Reported" for DB "Pending"
        db_status = "Pending" if new_status == "Reported" else new_status

        conn = sqlite3.connect("reports.db")
        cur = conn.cursor()
        cur.execute("UPDATE reports SET status = ? WHERE id = ?", (db_status, report_id))
        conn.commit()
        conn.close()

        return jsonify({"message": "Status updated", "status": new_status})
    except Exception as e:
        print("⚠️ Failed to update status:", e)
        return jsonify({"message": "Update failed"}), 500


@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")


# --- Database setup ---
def init_citizen_db():
    conn = sqlite3.connect('citizens.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS citizens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        dob TEXT,
        age INTEGER,
        gender TEXT,
        phone TEXT,
        email TEXT
    )''')
    conn.commit()
    conn.close()

def init_reports_db():
    conn = sqlite3.connect('reports.db')
    c = conn.cursor()
    # Create table with latitude/longitude included (safe for new DBs)
    c.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        location TEXT,
        description TEXT,
        image_path TEXT,
        severity TEXT,
        coverage REAL,
        preview_path TEXT,
        status TEXT DEFAULT "Pending",
        created_at TEXT,
        latitude REAL,
        longitude REAL
    )''')
    conn.commit()
    conn.close()
    # Ensure existing DB has new columns
    migrate_reports_db_add_coords()

def migrate_reports_db_add_coords():
    """Add latitude/longitude columns if they don't exist (safe ALTER)."""
    conn = sqlite3.connect('reports.db')
    cursor = conn.cursor()

    # Find existing columns
    cursor.execute("PRAGMA table_info(reports);")
    cols = [row[1] for row in cursor.fetchall()]

    if 'latitude' not in cols:
        try:
            cursor.execute("ALTER TABLE reports ADD COLUMN latitude REAL;")
        except Exception as e:
            print("Could not add latitude column:", e)
    if 'longitude' not in cols:
        try:
            cursor.execute("ALTER TABLE reports ADD COLUMN longitude REAL;")
        except Exception as e:
            print("Could not add longitude column:", e)

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect('citizens.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/test', methods=['GET'])
def test():
    return "✅ Flask backend is running fine!"


# --- API: Register Citizen ---
@app.route('/api/citizens', methods=['POST'])
def add_citizen():
    data = request.get_json(force=True)
    print("🟢 Received data:", data)

    name = data.get('name', '')
    dob = data.get('dob', '')
    age = data.get('age', '')
    gender = data.get('gender', '')
    phone = data.get('phone', '')
    email = data.get('email', '')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO citizens (name, dob, age, gender, phone, email) VALUES (?, ?, ?, ?, ?, ?)',
            (name, dob, age, gender, phone, email)
        )
        conn.commit()
        conn.close()
        print("✅ Citizen added successfully!")
        return jsonify({"message": "Registration successful!"}), 201
    except Exception as e:
        print("⚠️ Database error:", e)
        return jsonify({"message": "Database error"}), 500


# --- API: Report Issue ---
# --- API: Report Issue ---
@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("name")
        location = request.form.get("location")
        description = request.form.get("description")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        image = request.files.get("image")
        captured_image = request.form.get("captured_image")
        image_path = None

        os.makedirs("static/uploads", exist_ok=True)

        if image and image.filename:
            image_path = f"static/uploads/{image.filename}"
            image.save(image_path)
        elif captured_image:
            # Decode base64 string and save it as image
            header, data = captured_image.split(',', 1)
            image_data = base64.b64decode(data)
            image_filename = f"captured_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            image_path = f"static/uploads/{image_filename}"
            with open(image_path, "wb") as f:
                f.write(image_data)

        # These fields will be updated when the model is integrated
        severity = None
        coverage = None
        preview_path = None
        status = "Pending"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect("reports.db")
        cursor = conn.cursor()

        # Add latitude and longitude columns to the insert statement
        cursor.execute(
            '''INSERT INTO reports 
            (name, location, description, latitude, longitude, image_path, severity, coverage, preview_path, status, created_at) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (name, location, description, latitude, longitude, image_path, severity, coverage, preview_path, status, created_at)
        )
        conn.commit()
        conn.close()

        return render_template("success.html", message="Report submitted successfully!")

    return render_template("report_form.html")


@app.route("/employee/logout")
def employee_logout():
    session.pop("employee", None)
    return redirect(url_for("employee"))


# --- Run App ---
if __name__ == "__main__":
    init_citizen_db()
    init_reports_db()
    app.run(debug=True)
