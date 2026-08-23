"""
منصة التعرفة الجمركية الذكية - نظام تسجيل دخول واشتراكات
=========================================================
Flask + SQLite

تشغيل محلي:
    pip install -r requirements.txt
    python app.py

بيانات الأدمن الافتراضية عند أول تشغيل:
    اسم المستخدم: admin
    كلمة المرور:  admin123
    (يُنصح بشدّة بتغييرها مباشرة بعد أول دخول)
"""

import os
import sqlite3
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash

# ----------------------------------------------------------------------
# الإعدادات العامة
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("RENDER_DISK_PATH", BASE_DIR) 
DATABASE = os.path.join(DATA_DIR, "database.db")

app = Flask(__name__)
# مهم جداً: غيّر هذا المفتاح السري قبل النشر على الاستضافة
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key-in-production")

DATE_FMT = "%Y-%m-%d"

# بيانات الأدمن الافتراضية (تُستخدم فقط عند إنشاء قاعدة البيانات لأول مرة)
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

# الحد الأقصى لعدد الأجهزة/الجلسات المسموحة لكل مشترك بنفس الوقت
MAX_ACTIVE_SESSIONS = 2


# ----------------------------------------------------------------------
# الاتصال بقاعدة البيانات
# ----------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """ينشئ الجداول ومستخدم الأدمن الافتراضي إذا لم تكن قاعدة البيانات موجودة."""
    db = sqlite3.connect(DATABASE)
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',   -- 'admin' أو 'user'
            start_date TEXT NOT NULL,            -- تاريخ بداية الاشتراك YYYY-MM-DD
            duration_days INTEGER NOT NULL DEFAULT 30,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS active_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            session_token TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    db.commit()

    admin = db.execute(
        "SELECT id FROM users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)
    ).fetchone()

    if admin is None:
        db.execute(
            """INSERT INTO users
               (username, password_hash, role, start_date, duration_days, is_active, created_at)
               VALUES (?, ?, 'admin', ?, ?, 1, ?)""",
            (
                DEFAULT_ADMIN_USERNAME,
                generate_password_hash(DEFAULT_ADMIN_PASSWORD),
                datetime.now().strftime(DATE_FMT),
                36500,  # مدة طويلة جداً لحساب الأدمن (لا ينتهي عملياً)
                datetime.now().strftime(DATE_FMT),
            ),
        )
        db.commit()
        print(f"[+] تم إنشاء حساب أدمن افتراضي -> username: {DEFAULT_ADMIN_USERNAME} / password: {DEFAULT_ADMIN_PASSWORD}")

    db.close()


# ----------------------------------------------------------------------
# أدوات مساعدة
# ----------------------------------------------------------------------
def calc_remaining_days(start_date_str, duration_days):
    """يحسب عدد الأيام المتبقية للاشتراك (يمكن أن يكون سالباً إذا انتهى)."""
    start_date = datetime.strptime(start_date_str, DATE_FMT)
    expiry_date = start_date + timedelta(days=duration_days)
    remaining = (expiry_date.date() - datetime.now().date()).days
    return remaining, expiry_date.strftime(DATE_FMT)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        # تأكد أن جلسة هذا الجهاز ما زالت مفعّلة (ما تم إسقاطها من الأدمن أو من جهاز آخر)
        if session.get("role") != "admin":
            db = get_db()
            valid = db.execute(
                "SELECT id FROM active_sessions WHERE session_token = ?",
                (session.get("session_token"),),
            ).fetchone()
            if valid is None:
                session.clear()
                flash("تم تسجيل خروجك من هذا الجهاز. يرجى تسجيل الدخول مجدداً.")
                return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("هذه الصفحة مخصصة للأدمن فقط.", "error")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


# ----------------------------------------------------------------------
# المسارات (Routes)
# ----------------------------------------------------------------------
@app.route("/pricing.json")
def pricing_json():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "pricing.json")


@app.route("/pricing2.json")
def pricing2_json():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "pricing2.json")


@app.route("/")
def index():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.")
            return redirect(url_for("login"))

        if not user["is_active"]:
            flash("تم إيقاف هذا الحساب. يرجى التواصل مع الإدارة.")
            return redirect(url_for("login"))

        # التحقق من انتهاء الاشتراك (لا ينطبق على الأدمن عملياً لأن مدته طويلة جداً)
        remaining, _ = calc_remaining_days(user["start_date"], user["duration_days"])
        if user["role"] != "admin" and remaining < 0:
            flash("انتهت مدة اشتراكك. يرجى التواصل مع الإدارة لتجديد الاشتراك.")
            return redirect(url_for("login"))

        # التحقق من حد الأجهزة المسموح (لا ينطبق على الأدمن)
        if user["role"] != "admin":
            active_count = db.execute(
                "SELECT COUNT(*) AS c FROM active_sessions WHERE user_id = ?",
                (user["id"],),
            ).fetchone()["c"]

            if active_count >= MAX_ACTIVE_SESSIONS:
                flash(
                    f"وصلت للحد الأقصى ({MAX_ACTIVE_SESSIONS} أجهزة) لتسجيل الدخول بهذا الحساب. "
                    "يرجى تسجيل الخروج من أحد الأجهزة الأخرى أولاً، أو التواصل مع الإدارة."
                )
                return redirect(url_for("login"))

            session_token = secrets.token_hex(24)
            db.execute(
                "INSERT INTO active_sessions (user_id, session_token, created_at) VALUES (?, ?, ?)",
                (user["id"], session_token, datetime.now().strftime(DATE_FMT)),
            )
            db.commit()
            session["session_token"] = session_token

        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session["role"] = user["role"]

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    token = session.get("session_token")
    if token:
        db = get_db()
        db.execute("DELETE FROM active_sessions WHERE session_token = ?", (token,))
        db.commit()
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()

    if user is None:
        session.clear()
        return redirect(url_for("login"))

    remaining, expiry_date = calc_remaining_days(user["start_date"], user["duration_days"])

    # لو انتهى الاشتراك أثناء الجلسة، نخرجه فوراً
    if user["role"] != "admin" and (remaining < 0 or not user["is_active"]):
        session.clear()
        flash("انتهت مدة اشتراكك أو تم إيقاف حسابك. يرجى التواصل مع الإدارة.")
        return redirect(url_for("login"))

    return render_template(
        "user_dashboard.html",
        remaining_days=remaining,
        expiry_date=expiry_date,
    )


# ---------------------------- لوحة الأدمن ----------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    rows = db.execute("SELECT * FROM users ORDER BY role DESC, id DESC").fetchall()

    users = []
    for row in rows:
        remaining, _ = calc_remaining_days(row["start_date"], row["duration_days"])
        active_sessions_count = db.execute(
            "SELECT COUNT(*) AS c FROM active_sessions WHERE user_id = ?", (row["id"],)
        ).fetchone()["c"]
        users.append({
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "start_date": row["start_date"],
            "duration_days": row["duration_days"],
            "is_active": row["is_active"],
            "remaining_days": remaining,
            "active_sessions": active_sessions_count,
        })

    return render_template("admin_dashboard.html", users=users)


@app.route("/admin/add_user", methods=["POST"])
@admin_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    duration_days = request.form.get("duration_days", "30")

    if not username or not password:
        flash("يرجى تعبئة جميع الحقول.", "error")
        return redirect(url_for("admin_dashboard"))

    try:
        duration_days = int(duration_days)
        if duration_days < 1:
            raise ValueError
    except ValueError:
        flash("مدة الاشتراك يجب أن تكون رقماً صحيحاً أكبر من صفر.", "error")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    existing = db.execute(
        "SELECT id FROM users WHERE username = ?", (username,)
    ).fetchone()

    if existing:
        flash("اسم المستخدم موجود مسبقاً.", "error")
        return redirect(url_for("admin_dashboard"))

    db.execute(
        """INSERT INTO users
           (username, password_hash, role, start_date, duration_days, is_active, created_at)
           VALUES (?, ?, 'user', ?, ?, 1, ?)""",
        (
            username,
            generate_password_hash(password),
            datetime.now().strftime(DATE_FMT),
            duration_days,
            datetime.now().strftime(DATE_FMT),
        ),
    )
    db.commit()
    flash(f"تمت إضافة المشترك '{username}' بنجاح.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/toggle_user/<int:user_id>", methods=["POST"])
@admin_required
def toggle_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if user is None or user["role"] == "admin":
        flash("لا يمكن تنفيذ هذا الإجراء.", "error")
        return redirect(url_for("admin_dashboard"))

    new_status = 0 if user["is_active"] else 1
    db.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_status, user_id))
    db.commit()
    flash("تم تحديث حالة المستخدم.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/logout_sessions/<int:user_id>", methods=["POST"])
@admin_required
def logout_sessions(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if user is None or user["role"] == "admin":
        flash("لا يمكن تنفيذ هذا الإجراء.", "error")
        return redirect(url_for("admin_dashboard"))

    db.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))
    db.commit()
    flash(f"تم تسجيل خروج '{user['username']}' من كل الأجهزة.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if user is None or user["role"] == "admin":
        flash("لا يمكن حذف حساب الأدمن.", "error")
        return redirect(url_for("admin_dashboard"))

    db.execute("DELETE FROM active_sessions WHERE user_id = ?", (user_id,))
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    flash("تم حذف المستخدم.", "success")
    return redirect(url_for("admin_dashboard"))


# ----------------------------------------------------------------------
# نقطة انطلاق التطبيق
# ----------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    # عند النشر على استضافة حقيقية، استخدم خادم إنتاج مثل gunicorn
    # ولا تترك debug=True مفعّلاً
    app.run(host="0.0.0.0", port=5000, debug=True)
else:
    # عند التشغيل عبر gunicorn/WSGI في الاستضافة، تأكد من تهيئة القاعدة أيضاً
    init_db()
