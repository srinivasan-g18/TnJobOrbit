import os
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask, render_template, request, redirect, url_for, session,
    flash, jsonify, send_from_directory, abort
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "tnjoborbit.db"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "pdf", "doc", "docx", "txt", "png", "jpg", "jpeg",
    "webp", "xls", "xlsx", "ppt", "pptx"
}

INSTAGRAM_URL = "https://www.instagram.com/tnjoborbit?stkn=YmRnbWdnZHhsMzBw"
WHATSAPP_URL = "https://chat.whatsapp.com/J39OxYAuFp97hPPCa2BBpQ"


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        organization TEXT,
        category TEXT,
        description TEXT,
        eligibility TEXT,
        important_dates TEXT,
        official_url TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'published'
    );

    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT,
        subject TEXT,
        description TEXT,
        filename TEXT,
        original_filename TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'published'
    );

    CREATE TABLE IF NOT EXISTS materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT,
        description TEXT,
        filename TEXT,
        original_filename TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'published'
    );

    CREATE TABLE IF NOT EXISTS previous_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT,
        year TEXT,
        description TEXT,
        filename TEXT,
        original_filename TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'published'
    );

    CREATE TABLE IF NOT EXISTS important_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        url TEXT NOT NULL,
        category TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'published'
    );

    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT,
        subject TEXT,
        description TEXT,
        duration_minutes INTEGER NOT NULL DEFAULT 30,
        marks_per_question REAL NOT NULL DEFAULT 1,
        negative_marks REAL NOT NULL DEFAULT 0,
        difficulty TEXT DEFAULT 'Medium',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'published'
    );

    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER NOT NULL,
        question_text TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        explanation TEXT,
        question_order INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY(test_id) REFERENCES tests(id) ON DELETE CASCADE
    );
    """)
    # Create the first admin only if none exists.
    admin = conn.execute("SELECT id FROM admins LIMIT 1").fetchone()
    if not admin:
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "ChangeMe123!")
        conn.execute(
            "INSERT INTO admins(username,password_hash,created_at) VALUES(?,?,?)",
            (username, generate_password_hash(password), now())
        )

    defaults = [
        "TNPSC", "TRB", "TET", "Police", "Railway", "SSC",
        "Banking", "UPSC", "Group 1", "Group 2", "Group 4", "VAO", "Other"
    ]
    for name in defaults:
        conn.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (name,))
    conn.commit()
    conn.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file):
    if not file or not file.filename:
        return None, None
    if not allowed_file(file.filename):
        raise ValueError("File type is not allowed.")
    original = file.filename
    ext = Path(original).suffix.lower()
    safe_name = f"{secrets.token_hex(16)}{ext}"
    file.save(UPLOAD_DIR / safe_name)
    return safe_name, original


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return fn(*args, **kwargs)
    return wrapper


@app.context_processor
def inject_globals():
    return {
        "instagram_url": INSTAGRAM_URL,
        "whatsapp_url": WHATSAPP_URL,
        "admin_logged_in": bool(session.get("admin_id")),
        "year": datetime.now().year
    }


@app.route("/")
def home():
    conn = db()
    jobs = conn.execute(
        "SELECT * FROM jobs WHERE status='published' ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    notes = conn.execute(
        "SELECT * FROM notes WHERE status='published' ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    tests = conn.execute(
        "SELECT * FROM tests WHERE status='published' ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    conn.close()
    return render_template("index.html", jobs=jobs, notes=notes, tests=tests)


@app.route("/jobs")
def jobs():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    conn = db()
    sql = "SELECT * FROM jobs WHERE status='published'"
    params = []
    if q:
        sql += " AND (title LIKE ? OR organization LIKE ? OR description LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like]
    if category:
        sql += " AND category=?"
        params.append(category)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    categories = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("jobs.html", jobs=rows, categories=categories, q=q, selected_category=category)


@app.route("/notes")
def notes():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    conn = db()
    sql = "SELECT * FROM notes WHERE status='published'"
    params = []
    if q:
        sql += " AND (title LIKE ? OR subject LIKE ? OR description LIKE ?)"
        like = f"%{q}%"
        params += [like, like, like]
    if category:
        sql += " AND category=?"
        params.append(category)
    sql += " ORDER BY created_at DESC"
    rows = conn.execute(sql, params).fetchall()
    categories = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("notes.html", notes=rows, categories=categories, q=q, selected_category=category)


@app.route("/materials")
def materials():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM materials WHERE status='published' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("materials.html", materials=rows)


@app.route("/previous-questions")
def previous_questions():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM previous_questions WHERE status='published' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("previous_questions.html", questions=rows)


@app.route("/important-links")
def important_links():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM important_links WHERE status='published' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("important_links.html", links=rows)


@app.route("/tests")
def tests():
    conn = db()
    rows = conn.execute(
        "SELECT * FROM tests WHERE status='published' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return render_template("tests.html", tests=rows)


@app.route("/test/<int:test_id>")
def take_test(test_id):
    conn = db()
    test = conn.execute(
        "SELECT * FROM tests WHERE id=? AND status='published'", (test_id,)
    ).fetchone()
    if not test:
        conn.close()
        abort(404)
    questions = conn.execute(
        "SELECT * FROM questions WHERE test_id=? ORDER BY question_order,id", (test_id,)
    ).fetchall()
    conn.close()
    return render_template("take_test.html", test=test, questions=questions)


@app.route("/api/test/<int:test_id>/submit", methods=["POST"])
def submit_test(test_id):
    payload = request.get_json(silent=True) or {}
    answers = payload.get("answers", {})
    conn = db()
    test = conn.execute("SELECT * FROM tests WHERE id=?", (test_id,)).fetchone()
    if not test:
        conn.close()
        return jsonify({"error": "Test not found"}), 404
    questions = conn.execute(
        "SELECT * FROM questions WHERE test_id=? ORDER BY question_order,id", (test_id,)
    ).fetchall()
    score = 0
    correct = 0
    incorrect = 0
    unanswered = 0
    details = []
    for q in questions:
        selected = answers.get(str(q["id"]))
        if not selected:
            unanswered += 1
            result = "unanswered"
        elif selected.upper() == q["correct_option"].upper():
            correct += 1
            score += float(test["marks_per_question"])
            result = "correct"
        else:
            incorrect += 1
            score -= float(test["negative_marks"])
            result = "incorrect"
        details.append({
            "id": q["id"],
            "selected": selected,
            "correct": q["correct_option"],
            "result": result,
            "explanation": q["explanation"] or ""
        })
    total = len(questions)
    max_score = total * float(test["marks_per_question"])
    percentage = round((score / max_score) * 100, 2) if max_score else 0
    conn.close()
    return jsonify({
        "score": round(score, 2),
        "max_score": round(max_score, 2),
        "percentage": percentage,
        "correct": correct,
        "incorrect": incorrect,
        "unanswered": unanswered,
        "total": total,
        "details": details
    })


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # Only serve files that actually exist in the controlled upload folder.
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)


@app.route("/download/<kind>/<int:item_id>")
def download(kind, item_id):
    table_map = {
        "notes": "notes",
        "materials": "materials",
        "previous": "previous_questions"
    }
    table = table_map.get(kind)
    if not table:
        abort(404)
    conn = db()
    row = conn.execute(
        f"SELECT filename, original_filename FROM {table} WHERE id=? AND status='published'",
        (item_id,)
    ).fetchone()
    conn.close()
    if not row or not row["filename"]:
        abort(404)
    path = UPLOAD_DIR / row["filename"]
    if not path.exists():
        abort(404)
    return send_from_directory(UPLOAD_DIR, row["filename"], as_attachment=True,
                               download_name=row["original_filename"] or row["filename"])


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        conn = db()
        admin = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            flash("Welcome to the TnJobOrbit Admin Dashboard.", "success")
            return redirect(url_for("admin_dashboard"))
        flash("Invalid admin username or password.", "danger")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    counts = {}
    for key, table in [
        ("jobs", "jobs"), ("notes", "notes"), ("tests", "tests"),
        ("materials", "materials"), ("previous", "previous_questions"),
        ("links", "important_links")
    ]:
        counts[key] = conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"]
    recent_jobs = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 8").fetchall()
    recent_notes = conn.execute("SELECT * FROM notes ORDER BY created_at DESC LIMIT 8").fetchall()
    recent_tests = conn.execute("SELECT * FROM tests ORDER BY created_at DESC LIMIT 8").fetchall()
    conn.close()
    return render_template("admin/dashboard.html", counts=counts,
                           recent_jobs=recent_jobs, recent_notes=recent_notes,
                           recent_tests=recent_tests)


@app.route("/admin/categories", methods=["GET", "POST"])
@admin_required
def admin_categories():
    conn = db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            conn.execute("INSERT OR IGNORE INTO categories(name) VALUES(?)", (name,))
            conn.commit()
            flash("Category added.", "success")
        return redirect(url_for("admin_categories"))
    cats = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("admin/categories.html", categories=cats)


@app.route("/admin/categories/delete/<int:category_id>", methods=["POST"])
@admin_required
def admin_category_delete(category_id):
    conn = db()
    conn.execute("DELETE FROM categories WHERE id=?", (category_id,))
    conn.commit()
    conn.close()
    flash("Category deleted.", "success")
    return redirect(url_for("admin_categories"))


@app.route("/admin/jobs", methods=["GET", "POST"])
@admin_required
def admin_jobs():
    conn = db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Job title is required.", "danger")
        else:
            t = now()
            conn.execute("""
                INSERT INTO jobs(title,organization,category,description,eligibility,
                important_dates,official_url,created_at,updated_at,status)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (
                title, request.form.get("organization","").strip(),
                request.form.get("category","").strip(),
                request.form.get("description","").strip(),
                request.form.get("eligibility","").strip(),
                request.form.get("important_dates","").strip(),
                request.form.get("official_url","").strip(),
                t, t, request.form.get("status","published")
            ))
            conn.commit()
            flash("Government job published.", "success")
        conn.close()
        return redirect(url_for("admin_jobs"))
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    cats = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("admin/jobs.html", jobs=rows, categories=cats)


@app.route("/admin/jobs/delete/<int:item_id>", methods=["POST"])
@admin_required
def admin_job_delete(item_id):
    conn = db()
    conn.execute("DELETE FROM jobs WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Job deleted permanently by Admin.", "success")
    return redirect(url_for("admin_jobs"))


@app.route("/admin/jobs/toggle/<int:item_id>", methods=["POST"])
@admin_required
def admin_job_toggle(item_id):
    conn = db()
    row = conn.execute("SELECT status FROM jobs WHERE id=?", (item_id,)).fetchone()
    if row:
        new_status = "published" if row["status"] != "published" else "unpublished"
        conn.execute("UPDATE jobs SET status=?,updated_at=? WHERE id=?", (new_status, now(), item_id))
        conn.commit()
    conn.close()
    return redirect(url_for("admin_jobs"))


@app.route("/admin/notes", methods=["GET", "POST"])
@admin_required
def admin_notes():
    conn = db()
    if request.method == "POST":
        try:
            filename, original = save_upload(request.files.get("file"))
            title = request.form.get("title", "").strip()
            if not title:
                raise ValueError("Note title is required.")
            t = now()
            conn.execute("""
                INSERT INTO notes(title,category,subject,description,filename,original_filename,
                created_at,updated_at,status)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                title, request.form.get("category","").strip(),
                request.form.get("subject","").strip(),
                request.form.get("description","").strip(),
                filename, original, t, t, request.form.get("status","published")
            ))
            conn.commit()
            flash("Note uploaded successfully.", "success")
        except Exception as e:
            flash(str(e), "danger")
        conn.close()
        return redirect(url_for("admin_notes"))
    rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
    cats = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("admin/notes.html", notes=rows, categories=cats)


@app.route("/admin/notes/delete/<int:item_id>", methods=["POST"])
@admin_required
def admin_note_delete(item_id):
    conn = db()
    row = conn.execute("SELECT filename FROM notes WHERE id=?", (item_id,)).fetchone()
    if row and row["filename"]:
        try:
            (UPLOAD_DIR / row["filename"]).unlink(missing_ok=True)
        except OSError:
            pass
    conn.execute("DELETE FROM notes WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Note deleted permanently by Admin.", "success")
    return redirect(url_for("admin_notes"))


@app.route("/admin/notes/toggle/<int:item_id>", methods=["POST"])
@admin_required
def admin_note_toggle(item_id):
    conn = db()
    row = conn.execute("SELECT status FROM notes WHERE id=?", (item_id,)).fetchone()
    if row:
        new_status = "published" if row["status"] != "published" else "unpublished"
        conn.execute("UPDATE notes SET status=?,updated_at=? WHERE id=?", (new_status, now(), item_id))
        conn.commit()
    conn.close()
    return redirect(url_for("admin_notes"))


@app.route("/admin/materials", methods=["GET", "POST"])
@admin_required
def admin_materials():
    conn = db()
    if request.method == "POST":
        try:
            filename, original = save_upload(request.files.get("file"))
            title = request.form.get("title", "").strip()
            if not title:
                raise ValueError("Title is required.")
            t = now()
            conn.execute("""
                INSERT INTO materials(title,category,description,filename,original_filename,
                created_at,updated_at,status)
                VALUES(?,?,?,?,?,?,?,?)
            """, (
                title, request.form.get("category","").strip(),
                request.form.get("description","").strip(), filename, original,
                t, t, request.form.get("status","published")
            ))
            conn.commit()
            flash("Study material uploaded.", "success")
        except Exception as e:
            flash(str(e), "danger")
        conn.close()
        return redirect(url_for("admin_materials"))
    rows = conn.execute("SELECT * FROM materials ORDER BY created_at DESC").fetchall()
    cats = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("admin/materials.html", materials=rows, categories=cats)


@app.route("/admin/materials/delete/<int:item_id>", methods=["POST"])
@admin_required
def admin_material_delete(item_id):
    conn = db()
    row = conn.execute("SELECT filename FROM materials WHERE id=?", (item_id,)).fetchone()
    if row and row["filename"]:
        (UPLOAD_DIR / row["filename"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM materials WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Study material deleted.", "success")
    return redirect(url_for("admin_materials"))


@app.route("/admin/previous", methods=["GET", "POST"])
@admin_required
def admin_previous():
    conn = db()
    if request.method == "POST":
        try:
            filename, original = save_upload(request.files.get("file"))
            title = request.form.get("title", "").strip()
            if not title:
                raise ValueError("Title is required.")
            t = now()
            conn.execute("""
                INSERT INTO previous_questions(title,category,year,description,filename,original_filename,
                created_at,updated_at,status)
                VALUES(?,?,?,?,?,?,?,?,?)
            """, (
                title, request.form.get("category","").strip(),
                request.form.get("year","").strip(),
                request.form.get("description","").strip(),
                filename, original, t, t, request.form.get("status","published")
            ))
            conn.commit()
            flash("Previous-year paper uploaded.", "success")
        except Exception as e:
            flash(str(e), "danger")
        conn.close()
        return redirect(url_for("admin_previous"))
    rows = conn.execute("SELECT * FROM previous_questions ORDER BY created_at DESC").fetchall()
    cats = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("admin/previous.html", questions=rows, categories=cats)


@app.route("/admin/previous/delete/<int:item_id>", methods=["POST"])
@admin_required
def admin_previous_delete(item_id):
    conn = db()
    row = conn.execute("SELECT filename FROM previous_questions WHERE id=?", (item_id,)).fetchone()
    if row and row["filename"]:
        (UPLOAD_DIR / row["filename"]).unlink(missing_ok=True)
    conn.execute("DELETE FROM previous_questions WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Previous paper deleted.", "success")
    return redirect(url_for("admin_previous"))


@app.route("/admin/links", methods=["GET", "POST"])
@admin_required
def admin_links():
    conn = db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        url = request.form.get("url", "").strip()
        if not title or not url:
            flash("Title and URL are required.", "danger")
        else:
            t = now()
            conn.execute("""
                INSERT INTO important_links(title,description,url,category,created_at,updated_at,status)
                VALUES(?,?,?,?,?,?,?)
            """, (
                title, request.form.get("description","").strip(), url,
                request.form.get("category","").strip(), t, t,
                request.form.get("status","published")
            ))
            conn.commit()
            flash("Important link added.", "success")
        conn.close()
        return redirect(url_for("admin_links"))
    rows = conn.execute("SELECT * FROM important_links ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("admin/links.html", links=rows)


@app.route("/admin/links/delete/<int:item_id>", methods=["POST"])
@admin_required
def admin_link_delete(item_id):
    conn = db()
    conn.execute("DELETE FROM important_links WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Link deleted.", "success")
    return redirect(url_for("admin_links"))


@app.route("/admin/tests", methods=["GET", "POST"])
@admin_required
def admin_tests():
    conn = db()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Test title is required.", "danger")
            conn.close()
            return redirect(url_for("admin_tests"))
        t = now()
        cur = conn.execute("""
            INSERT INTO tests(title,category,subject,description,duration_minutes,
            marks_per_question,negative_marks,difficulty,created_at,updated_at,status)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (
            title, request.form.get("category","").strip(),
            request.form.get("subject","").strip(),
            request.form.get("description","").strip(),
            int(request.form.get("duration_minutes", 30)),
            float(request.form.get("marks_per_question", 1)),
            float(request.form.get("negative_marks", 0)),
            request.form.get("difficulty","Medium"),
            t, t, request.form.get("status","published")
        ))
        conn.commit()
        test_id = cur.lastrowid
        conn.close()
        flash("Test created. Add questions now.", "success")
        return redirect(url_for("admin_test_questions", test_id=test_id))
    rows = conn.execute("SELECT * FROM tests ORDER BY created_at DESC").fetchall()
    cats = conn.execute("SELECT name FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template("admin/tests.html", tests=rows, categories=cats)


@app.route("/admin/tests/<int:test_id>/questions", methods=["GET", "POST"])
@admin_required
def admin_test_questions(test_id):
    conn = db()
    test = conn.execute("SELECT * FROM tests WHERE id=?", (test_id,)).fetchone()
    if not test:
        conn.close()
        abort(404)
    if request.method == "POST":
        conn.execute("""
            INSERT INTO questions(test_id,question_text,option_a,option_b,option_c,option_d,
            correct_option,explanation,question_order)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            test_id,
            request.form.get("question_text","").strip(),
            request.form.get("option_a","").strip(),
            request.form.get("option_b","").strip(),
            request.form.get("option_c","").strip(),
            request.form.get("option_d","").strip(),
            request.form.get("correct_option","A").upper(),
            request.form.get("explanation","").strip(),
            int(request.form.get("question_order", 0))
        ))
        conn.commit()
        flash("Question added.", "success")
        return redirect(url_for("admin_test_questions", test_id=test_id))
    questions = conn.execute(
        "SELECT * FROM questions WHERE test_id=? ORDER BY question_order,id", (test_id,)
    ).fetchall()
    conn.close()
    return render_template("admin/questions.html", test=test, questions=questions)


@app.route("/admin/questions/delete/<int:question_id>", methods=["POST"])
@admin_required
def admin_question_delete(question_id):
    conn = db()
    row = conn.execute("SELECT test_id FROM questions WHERE id=?", (question_id,)).fetchone()
    if row:
        test_id = row["test_id"]
        conn.execute("DELETE FROM questions WHERE id=?", (question_id,))
        conn.commit()
        conn.close()
        flash("Question deleted.", "success")
        return redirect(url_for("admin_test_questions", test_id=test_id))
    conn.close()
    return redirect(url_for("admin_tests"))


@app.route("/admin/tests/delete/<int:test_id>", methods=["POST"])
@admin_required
def admin_test_delete(test_id):
    conn = db()
    conn.execute("DELETE FROM tests WHERE id=?", (test_id,))
    conn.commit()
    conn.close()
    flash("Test and its questions deleted by Admin.", "success")
    return redirect(url_for("admin_tests"))


@app.route("/admin/tests/toggle/<int:test_id>", methods=["POST"])
@admin_required
def admin_test_toggle(test_id):
    conn = db()
    row = conn.execute("SELECT status FROM tests WHERE id=?", (test_id,)).fetchone()
    if row:
        new_status = "published" if row["status"] != "published" else "unpublished"
        conn.execute("UPDATE tests SET status=?,updated_at=? WHERE id=?", (new_status, now(), test_id))
        conn.commit()
    conn.close()
    return redirect(url_for("admin_tests"))


@app.route("/admin/password", methods=["GET", "POST"])
@admin_required
def admin_password():
    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")
        conn = db()
        admin = conn.execute("SELECT * FROM admins WHERE id=?", (session["admin_id"],)).fetchone()
        if not check_password_hash(admin["password_hash"], current):
            flash("Current password is incorrect.", "danger")
        elif len(new) < 8:
            flash("New password must be at least 8 characters.", "danger")
        elif new != confirm:
            flash("New passwords do not match.", "danger")
        else:
            conn.execute(
                "UPDATE admins SET password_hash=? WHERE id=?",
                (generate_password_hash(new), session["admin_id"])
            )
            conn.commit()
            flash("Admin password changed successfully.", "success")
        conn.close()
    return render_template("admin/password.html")


@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "TnJobOrbit",
        "short_name": "TnJobOrbit",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#0b1f3a",
        "icons": [
            {"src": "/static/logo.png", "sizes": "512x512", "type": "image/png"}
        ]
    })


@app.route("/service-worker.js")
def service_worker():
    return app.send_static_file("service-worker.js")


@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum upload size is 50 MB.", "danger")
    return redirect(request.referrer or url_for("home"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
