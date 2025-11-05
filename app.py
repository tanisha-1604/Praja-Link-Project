from flask import Flask, request, jsonify, render_template
from flask import redirect, url_for, session
from flask_cors import CORS
from model.severity_calc_final import calculate_severity
import numpy as np
import cv2
import pandas as pd
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
    return render_template("services.html")
    return render_template("services.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name")
        dob = request.form.get("dob")
        age = request.form.get("age")
        gender = request.form.get("gender")
        phone = request.form.get("phone")
        email = request.form.get("email")

        # --- CSV-based insert ---
    if not os.path.exists("citizens.csv"):
        init_citizen_db()

        df = pd.read_csv("citizens.csv")
        new_id = len(df) + 1
        new_row = pd.DataFrame([{
            "id": new_id,
            "name": name,
            "dob": dob,
            "age": age,
            "gender": gender,
            "phone": phone,
            "email": email
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv("citizens.csv", index=False)

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
        if not os.path.exists("reports.csv"):
            init_reports_db()

        df = pd.read_csv("reports.csv")
        df = df.sort_values(by="created_at", ascending=False)
        reports = df.to_dict(orient="records")
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
        if not os.path.exists("reports.csv"):
            init_reports_db()

        df = pd.read_csv("reports.csv")
        df = df.sort_values(by="created_at", ascending=False)
        reports = df.to_dict(orient="records")
        # Calculate status counts
        status_counts = {"all": len(reports), "Reported": 0, "In Review": 0, "Resolved": 0}
        for report in reports:
            raw_status = report['status'] or 'Pending'
            display_status = 'Reported' if raw_status == 'Pending' else raw_status
            if display_status in status_counts:
                status_counts[display_status] += 1
 
    except Exception as e:
        print("⚠️ Error loading reports for admin dashboard:", e)
        reports = []
        status_counts = {"all": 0, "Reported": 0, "In Review": 0, "Resolved": 0}

    return render_template("admin_dashboard.html", reports=reports, status_counts=status_counts)


@app.route("/update_status/<int:report_id>", methods=["POST"])
def update_status(report_id: int):
    if "employee" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    try:
        data = request.get_json(force=True)
        new_status = (data.get("status") or "").strip()
        db_status = "Pending" if new_status == "Reported" else new_status

        if not os.path.exists("reports.csv"):
            init_reports_db()

        df = pd.read_csv("reports.csv")
        if report_id in df['id'].values:
            df.loc[df['id'] == report_id, 'status'] = db_status
            df.to_csv("reports.csv", index=False)
            return jsonify({"message": "Status updated", "status": new_status})
        else:
            return jsonify({"message": "Report not found"}), 404
        
    except Exception as e:
        print("⚠️ Failed to update status:", e)
        return jsonify({"message": "Update failed"}), 500


@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/admin")
def admin():
    return render_template("admin.html")


# --- Database setup ---
def init_citizen_db():
    """Ensure citizens.csv exists with correct headers."""
    if not os.path.exists('citizens.csv'):
        df = pd.DataFrame(columns=['id', 'name', 'dob', 'age', 'gender', 'phone', 'email'])
        df.to_csv('citizens.csv', index=False)
        print("✅ Created citizens.csv")

def init_reports_db():
    """Ensure reports.csv exists with correct headers."""
    if not os.path.exists('reports.csv'):
        df = pd.DataFrame(columns=[
            'id', 'name', 'location', 'description', 'category',
            'image_path', 'severity', 'coverage', 'preview_path',
            'status', 'created_at', 'latitude', 'longitude'
        ])
        df.to_csv('reports.csv', index=False)
        print("✅ Created reports.csv")



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
        if not os.path.exists("citizens.csv"):
            init_citizen_db()

        df = pd.read_csv("citizens.csv")
        new_id = len(df) + 1
        new_row = pd.DataFrame([{
            "id": new_id,
            "name": name,
            "dob": dob,
            "age": age,
            "gender": gender,
            "phone": phone,
            "email": email
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv("citizens.csv", index=False)
        print("✅ Citizen added successfully!")
        return jsonify({"message": "Registration successful!"}), 201
    
    except Exception as e:
        print("⚠️ Failed to add citizen:", e)
        return jsonify({"error": "Failed to add citizen"}), 500

# --- API: Report Issue ---
@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        name = request.form.get("name")
        location = request.form.get("location")
        description = request.form.get("description")
        category = request.form.get("category")
        latitude = request.form.get("latitude")
        longitude = request.form.get("longitude")
        image = request.files.get("image")
        captured_image = request.form.get("captured_image")
        image_path = None

        os.makedirs("static/uploads", exist_ok=True)

        # --- Save uploaded or captured image ---
        if image and image.filename:
            image_path = f"static/uploads/{image.filename}"
            image.save(image_path)
        elif captured_image:
            header, data = captured_image.split(',', 1)
            image_data = base64.b64decode(data)
            image_filename = f"captured_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            image_path = f"static/uploads/{image_filename}"
            with open(image_path, "wb") as f:
                f.write(image_data)

        # ✅ Store form data temporarily in session until analysis completes
        session["report_data"] = {
            "name": name,
            "location": location,
            "description": description,
            "category": category,
            "latitude": latitude,
            "longitude": longitude,
            "image_path": image_path
        }

        # Redirect to analysis page for polygon marking
        image_name = os.path.basename(image_path)
        return redirect(url_for("analyze", image_name=image_name))

    return render_template("report_form.html")


@app.route("/analyze", methods=["GET"])
def analyze():
    image_name = request.args.get("image_name")
    category = "general"  # You can make this dynamic later
    return render_template("analyze_final.html", image_name=image_name, category=category)

@app.route("/process_polygon", methods=["POST"])
def process_polygon():
    data = request.get_json(force=True)
    points = data.get("points", [])
    image_name = data.get("image_name", "")
    category = data.get("category", "")

    image_path = os.path.join("static", "uploads", image_name)

    # --- Run your existing model ---
    try:
        coverage, severity = calculate_severity(image_path, points)
    except Exception as e:
        print("⚠️ Model failed:", e)
        return jsonify({"error": "Model failed"}), 500

    # Retrieve temporarily saved data
    report_data = session.pop("report_data", {})
    name = report_data.get("name")
    location = report_data.get("location")
    description = report_data.get("description")
    category_form = report_data.get("category")
    latitude = report_data.get("latitude")
    longitude = report_data.get("longitude")

    # --- Save or update final report in DB ---
    status = "Pending"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    preview_path = None

    if not os.path.exists("reports.csv"):
        init_reports_db()

    df = pd.read_csv("reports.csv")
    image_exists = df['image_path'].astype(str).str.contains(image_name, na=False)

    if image_exists.any():
        df.loc[image_exists, ['severity', 'coverage']] = [severity, coverage]
    else:
        new_id = len(df) + 1
        new_row = pd.DataFrame([{
            "id": new_id,
            "name": name,
            "location": location,
            "description": description,
            "category": category_form,
            "latitude": latitude,
            "longitude": longitude,
            "image_path": image_path,
            "severity": severity,
            "coverage": coverage,
            "preview_path": None,
            "status": status,
            "created_at": created_at
    }])
    df = pd.concat([df, new_row], ignore_index=True)

    df.to_csv("reports.csv", index=False)
    print(f"✅ Saved report: {severity=}, {coverage=}")
    return jsonify({"severity": severity, "coverage": coverage})

@app.route("/thankyou")
def thankyou():
    return render_template("success.html", message="✅ Thank You for Your Contribution! 🌱 Together, we’re building a cleaner and safer community.")


@app.route("/employee/logout")
def employee_logout():
    session.pop("employee", None)
    return redirect(url_for("employee"))


@app.route("/report/<int:report_id>")
def report_details(report_id):
    """Display detailed view of a single report"""
    try:
        if not os.path.exists("reports.csv"):
            init_reports_db()

        df = pd.read_csv("reports.csv")
        report = df.loc[df['id'] == report_id].to_dict(orient="records")
        report = report[0] if report else None
        
        if not report:
            return render_template("error.html", message="Report not found"), 404
        
        return render_template("report_details.html", report=report)
    except Exception as e:
        print("⚠️ Error loading report:", e)
        return render_template("error.html", message="Could not load report"), 500


# --- Run App ---
if __name__ == "__main__":
    init_citizen_db()
    init_reports_db()
    app.run(debug=True)
