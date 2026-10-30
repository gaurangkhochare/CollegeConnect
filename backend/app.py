from flask_cors import CORS
from db import get_db_connection
from flask import Flask, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY must be set.")

configured_origins = os.environ.get("CORS_ALLOWED_ORIGINS")
allowed_origins = (
    [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    if configured_origins is not None
    else ["http://127.0.0.1:8000", "http://localhost:8000"]
)
if allowed_origins:
    CORS(app, supports_credentials=True, origins=allowed_origins)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "").lower()
    == "true",
)


@app.route("/")
def home():
    return send_from_directory(PROJECT_ROOT, "index.html")


@app.route("/<path:filename>")
def frontend_file(filename):
    allowed_pages = {
        "analytics.html",
        "classrooms.html",
        "complaints.html",
        "dashboard.html",
        "index.html",
        "login.html",
        "timetable.html",
    }
    if filename not in allowed_pages and not filename.startswith(
        ("assets/", "css/", "js/")
    ):
        return jsonify({"error": "Not found."}), 404

    return send_from_directory(PROJECT_ROOT, filename)


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    role = str(data.get("role", "student")).strip().lower()

    if not name or not email or len(password) < 8:
        return (
            jsonify(
                {
                    "error": "Name, email and password (minimum 8 characters) are required."
                }
            ),
            400,
        )

    if role != "student":
        return jsonify({"error": "Public registration is limited to students."}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))

        if cursor.fetchone():
            return jsonify({"error": "Email is already registered."}), 409

        password_hash = generate_password_hash(password)
        cursor.execute(
            """
                INSERT INTO users (name, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
            """,
            (name, email, password_hash, role),
        )

        conn.commit()

        return jsonify({"message": "Registration successful."}), 201

    except Exception:
        app.logger.exception("Registration failed")
        return jsonify({"error": "Could not register user."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
                SELECT id, name, email, password_hash, role
                FROM users
                WHERE email = %s
            """,
            (email,),
        )

        user = cursor.fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            return jsonify({"error": "Invalid email or password."}), 401

        session.clear()
        session["user_id"] = user["id"]
        session["role"] = user["role"]

        return jsonify(
            {
                "message": "Login successful.",
                "user": {
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"],
                    "role": user["role"],
                },
            }
        )

    except Exception:
        app.logger.exception("Login failed")
        return jsonify({"error": "Could not log in."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


@app.route("/api/health")
def health():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "success", "database": "connected"})

    except Exception:
        app.logger.exception("Database health check failed")
        return jsonify({"status": "error", "message": "Database unavailable."}), 500


@app.route("/api/complaints", methods=["GET"])
def get_complaints():
    if "user_id" not in session:
        return jsonify({"error": "Login required."}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
          SELECT
                    c.id,
                    c.category,
                    c.location,
                    c.title,
                    c.description,
                    c.priority,
                    c.status,
                    c.created_at,
                    c.reported_by,
                    c.assigned_to,
                    u.name AS assigned_faculty_name
          FROM complaints c
          LEFT JOIN users u ON c.assigned_to = u.id
          ORDER BY c.created_at DESC
        """)

        complaints = cursor.fetchall()
        cursor.close()
        conn.close()

        return jsonify(complaints)

    except Exception:
        app.logger.exception("Could not load complaints")
        return jsonify({"error": "Could not load complaints."}), 500


from flask import request


@app.route("/api/complaints", methods=["POST"])
def create_complaint():
    if "user_id" not in session or session.get("role") not in ("student", "cr"):
        return jsonify({"error": "Only students and CRs can report complaints."}), 403

    data = request.get_json(silent=True) or {}
    category = str(data.get("category", "")).strip()
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    location = str(data.get("location", "")).strip() or None
    priority = str(data.get("priority", "medium")).lower()

    if not category or not title or not description:
        return jsonify({"error": "Category, title and description are required."}), 400

    if priority not in ["low", "medium", "high", "critical"]:
        return jsonify({"error": "Invalid priority."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
                INSERT INTO complaints
                        (category, location, title, description, priority, reported_by)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                category,
                location,
                title,
                description,
                priority,
                session["user_id"],
            ),
        )

        conn.commit()
        complaint_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return (
            jsonify(
                {"message": "Complaint submitted successfully.", "id": complaint_id}
            ),
            201,
        )

    except Exception:
        app.logger.exception("Could not create complaint")
        return jsonify({"error": "Could not submit complaint."}), 500


@app.route("/api/timetable", methods=["GET"])
def get_timetable():
    if "user_id" not in session:
        return jsonify({"error": "Login required."}), 401

    branch = request.args.get("branch", "").strip().upper()
    division = request.args.get("division", "").strip().upper()
    day = request.args.get("day", "").strip().upper()

    if not branch or not division:
        return jsonify({"error": "Please select branch and division."}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = """
            SELECT
                    branch,
                    year_level,
                    division,
                    day,
                    time_slot,
                    subject_code,
                    prof_code,
                    location
            FROM timetable
            WHERE UPPER(TRIM(branch)) = %s
                AND UPPER(TRIM(division)) = %s
        """

        params = [branch, division]

        if day:
            query += " AND UPPER(TRIM(day)) = %s"
            params.append(day)

        query += """
            ORDER BY
                FIELD(
                    UPPER(TRIM(day)),
                        'MONDAY', 'TUESDAY', 'WEDNESDAY',
                        'THURSDAY', 'FRIDAY', 'SATURDAY'
                    ),
                    STR_TO_DATE(
                        SUBSTRING_INDEX(time_slot, '-', 1),
                        '%H:%i'
                    )
        """

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()

        return jsonify(
            {
                "branch": branch,
                "division": division,
                "day": day or "ALL",
                "count": len(rows),
                "results": rows,
            }
        )

    except Exception:
        app.logger.exception("Timetable query failed")
        return jsonify({"error": "Could not load timetable."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/classrooms/available", methods=["GET"])
def available_classrooms():
    from flask import request
    from datetime import datetime

    day = request.args.get("day", "").strip().upper()
    start = request.args.get("start", "").strip()
    end = request.args.get("end", "").strip()
    branch = request.args.get("branch", "").strip().upper()
    division = request.args.get("division", "").strip().upper()

    if "user_id" not in session:
        return jsonify({"error": "Login required."}), 401

    if not day or not start or not end:
        return jsonify({"error": "Please provide day, start and end"}), 400

    try:
        start_time = datetime.strptime(start, "%H:%M")
        end_time = datetime.strptime(end, "%H:%M")

    except ValueError:
        return jsonify({"error": "Time must use HH:MM format"}), 400

    if start_time >= end_time:
        return jsonify({"error": "End time must be after start time"}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT DISTINCT
            TRIM(c.location) AS location,
            c.status,
            'available' AS availability
            FROM classrooms c
            WHERE c.status = 'available'
            AND c.location IS NOT NULL
            AND TRIM(c.location) <> ''
            AND TRIM(c.location) NOT REGEXP '^[0-9*?]+$'
            AND c.location NOT LIKE '%â%'
            AND NOT EXISTS (
                SELECT 1
                FROM timetable t
                WHERE TRIM(t.location) = TRIM(c.location)
                    AND UPPER(TRIM(t.day)) = %s
                    AND t.time_slot REGEXP
                                '^[0-9]{2}:[0-9]{2}-[0-9]{2}:[0-9]{2}$'
                    AND STR_TO_DATE(
                                SUBSTRING_INDEX(t.time_slot, '-', 1),
                                '%H:%i'
                    ) < STR_TO_DATE(%s, '%H:%i')
                    AND STR_TO_DATE(
                                SUBSTRING_INDEX(t.time_slot, '-', -1),
                                '%H:%i'
                    ) > STR_TO_DATE(%s, '%H:%i')
            )
            AND (
                %s = ''
                OR EXISTS (
                    SELECT 1
                    FROM timetable t
                    WHERE TRIM(t.location) = TRIM(c.location)
                        AND UPPER(TRIM(t.branch)) = %s
                )
            )
            AND (
                %s = ''
                OR EXISTS (
                    SELECT 1
                    FROM timetable t
                    WHERE TRIM(t.location) = TRIM(c.location)
                        AND UPPER(TRIM(t.branch)) = %s
                        AND UPPER(TRIM(t.division)) = %s
                )
            )
            ORDER BY location
        """,
            (day, end, start, branch, branch, division, branch, division),
        )

        results = cursor.fetchall()
        return jsonify({"day": day, "start": start, "end": end, "results": results})

    except Exception:
        app.logger.exception("Classroom availability query failed")
        return jsonify({"error": "Could not check availability"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/faculty", methods=["GET"])
def get_faculty():
    if "user_id" not in session or session.get("role") != "cr":
        return jsonify({"error": "Only logged-in CRs can view faculty."}), 403

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, email
            FROM users
            WHERE role = 'professor'
            ORDER BY name
        """)

        return jsonify(cursor.fetchall())

    except Exception:
        app.logger.exception("Could not load faculty")
        return jsonify({"error": "Could not load faculty list."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/complaints/<int:complaint_id>/assign", methods=["POST"])
def assign_complaint(complaint_id):
    if "user_id" not in session or session.get("role") != "cr":
        return jsonify({"error": "Only logged-in CRs can assign complaints."}), 403

    data = request.get_json(silent=True) or {}
    faculty_id = data.get("faculty_id")

    if not faculty_id:
        return jsonify({"error": "Please select a faculty member."}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id FROM users WHERE id = %s AND role = 'professor'", (faculty_id,)
        )
        if not cursor.fetchone():
            return jsonify({"error": "Invalid faculty account."}), 400
        cursor.execute("SELECT id FROM complaints WHERE id = %s", (complaint_id,))

        if not cursor.fetchone():
            return jsonify({"error": "Complaint not found."}), 404

        cursor.execute(
            """
                UPDATE complaints
                SET assigned_to = %s, status = 'in_progress'
                WHERE id = %s
            """,
            (faculty_id, complaint_id),
        )

        conn.commit()
        return jsonify({"message": "Complaint assigned to faculty successfully."})

    except Exception:
        app.logger.exception("Complaint assignment failed")
        if conn:
            conn.rollback()

        return jsonify({"error": "Could not assign complaint."}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/my-complaints", methods=["GET"])
def get_my_complaints():
    # Only an authenticated professor may view complaints assigned to them.
    if "user_id" not in session or session.get("role") != "professor":
        return (
            jsonify(
                {
                    "error": "Only logged-in professors can view their assigned complaints."
                }
            ),
            403,
        )

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                c.id,
                c.category,
                c.location,
                c.title,
                c.description,
                c.priority,
                c.status,
                c.created_at,
                c.assigned_to,
                u.name AS assigned_faculty_name
            FROM complaints c
            LEFT JOIN users u ON c.assigned_to = u.id
            WHERE c.assigned_to = %s
            ORDER BY c.created_at DESC
        """,
            (session["user_id"],),
        )
        complaints = cursor.fetchall()
        return jsonify(complaints), 200
    except Exception:
        app.logger.exception("Could not load professor complaints")
        return jsonify({"error": "Could not load assigned complaints."}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/api/me", methods=["GET"])
def get_current_user():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id, name, email, role
            FROM users
            WHERE id = %s
            """,
            (session["user_id"],),
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"user": user}), 200

    finally:
        cursor.close()
        conn.close()


@app.route("/api/complaints/<int:complaint_id>/status", methods=["PATCH"])
def update_complaint_status(complaint_id):
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    if session.get("role") != "professor":
        return jsonify({"error": "Only professors can resolve complaints"}), 403

    data = request.get_json(silent=True) or {}
    status = str(data.get("status", "")).lower()

    if status != "resolved":
        return jsonify({"error": "Only resolved status is allowed"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT id
            FROM complaints
            WHERE id = %s AND assigned_to = %s
            """,
            (complaint_id, session["user_id"]),
        )

        complaint = cursor.fetchone()

        if not complaint:
            return jsonify({"error": "Complaint not found or not assigned to you"}), 404

        cursor.execute(
            """
            UPDATE complaints
            SET status = 'resolved', resolved_at = NOW()
            WHERE id = %s AND assigned_to = %s
            """,
            (complaint_id, session["user_id"]),
        )

        conn.commit()

        return jsonify({"message": "Complaint marked as resolved successfully"}), 200

    except Exception as error:
        conn.rollback()
        app.logger.exception("Failed to update complaint status")
        return jsonify({"error": "Could not update complaint status"}), 500

    finally:
        cursor.close()
        conn.close()


@app.route("/api/dashboard/stats", methods=["GET"])
def dashboard_stats():
    if "user_id" not in session:
        return jsonify({"error": "Login required"}), 401

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) = 'available'
                    THEN 1 ELSE 0 END
                ), 0) AS available_classrooms,

                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) IN ('occupied', 'inactive')
                    THEN 1 ELSE 0 END
                ), 0) AS occupied_classrooms,

                COALESCE(SUM(
                    CASE WHEN LOWER(TRIM(status)) = 'maintenance'
                    THEN 1 ELSE 0 END
                ), 0) AS maintenance
            FROM classrooms
        """)

        classroom_stats = cursor.fetchone() or {}

        cursor.execute("""
            SELECT COUNT(*) AS active_complaints
            FROM complaints
            WHERE status IN ('pending', 'in_progress')
        """)

        complaint_stats = cursor.fetchone() or {}

        return (
            jsonify(
                {
                    "available_classrooms": int(
                        classroom_stats.get("available_classrooms", 0)
                    ),
                    "occupied_classrooms": int(
                        classroom_stats.get("occupied_classrooms", 0)
                    ),
                    "active_complaints": int(
                        complaint_stats.get("active_complaints", 0)
                    ),
                    "maintenance": int(classroom_stats.get("maintenance", 0)),
                }
            ),
            200,
        )

    except Exception:
        app.logger.exception("Could not load dashboard statistics")
        return jsonify({"error": "Could not load dashboard statistics"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "").lower() == "true",
    )
