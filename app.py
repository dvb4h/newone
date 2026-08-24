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
import hashlib
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g, send_from_directory, jsonify
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

# مدة صلاحية الجلسة على الجهاز الواحد (بالأيام) — تخلي المستخدم مسجّل دخول
# حتى لو أغلق المتصفح تماماً، بدل ما يُطلب منه الدخول من جديد في كل مرة
SESSION_LIFETIME_DAYS = 30
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=SESSION_LIFETIME_DAYS)

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
            device_fingerprint TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS calculation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            hs_code TEXT NOT NULL,
            description TEXT,
            price TEXT,
            added_at TEXT NOT NULL,
            UNIQUE(user_id, hs_code),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    db.commit()

    # ترحيل بسيط: إضافة عمود device_fingerprint لو القاعدة كانت موجودة من قبل بدونه
    existing_cols = [row[1] for row in db.execute("PRAGMA table_info(active_sessions)").fetchall()]
    if "device_fingerprint" not in existing_cols:
        db.execute("ALTER TABLE active_sessions ADD COLUMN device_fingerprint TEXT")
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


def get_device_fingerprint():
    """
    بصمة تقريبية للجهاز مبنية على نوع المتصفح + عنوان IP.
    تستخدم لمنع احتساب نفس الجهاز كـ'جهاز جديد' في كل تسجيل دخول متكرر
    (مثلاً بعد إغلاق مفاجئ للمتصفح وإعادة فتحه أكثر من مرة).
    ملاحظة: ليست مثالية 100% (تغيّر الـ IP قد يُنشئ بصمة مختلفة)، لكنها تقلل
    المشكلة بشكل كبير في الحالات الشائعة.
    """
    ua = request.headers.get("User-Agent", "")
    ip = request.remote_addr or ""
    raw = f"{ua}|{ip}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def cleanup_stale_sessions(db, user_id):
    """
    يحذف جلسات هذا المستخدم الأقدم من SESSION_LIFETIME_DAYS.
    يمنع بقاء 'أجهزة وهمية' تشغل مكاناً بعد فقدان الكوكي (مسح المتصفح، جهاز جديد...)
    بدون ما يحتاج المستخدم أو الأدمن يتدخل يدوياً.
    """
    cutoff = (datetime.now() - timedelta(days=SESSION_LIFETIME_DAYS)).strftime(DATE_FMT)
    db.execute(
        "DELETE FROM active_sessions WHERE user_id = ? AND created_at < ?",
        (user_id, cutoff),
    )
    db.commit()


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


@app.route("/pricing3.json")
def pricing3_json():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "pricing3.json")


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
            # تنظيف الجلسات المهجورة (أقدم من SESSION_LIFETIME_DAYS) قبل فحص العدد
            cleanup_stale_sessions(db, user["id"])

            device_fp = get_device_fingerprint()

            # لو نفس الجهاز (نفس المتصفح + نفس IP) عنده جلسة قديمة، نحذفها ونعيد
            # استخدام مكانها بدل ما نحتسبه "جهاز جديد" (يعالج حالة الإغلاق المفاجئ
            # وإعادة تسجيل الدخول أكثر من مرة من نفس الجهاز)
            db.execute(
                "DELETE FROM active_sessions WHERE user_id = ? AND device_fingerprint = ?",
                (user["id"], device_fp),
            )
            db.commit()

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
                "INSERT INTO active_sessions (user_id, session_token, device_fingerprint, created_at) VALUES (?, ?, ?, ?)",
                (user["id"], session_token, device_fp, datetime.now().strftime(DATE_FMT)),
            )
            db.commit()
            session["session_token"] = session_token

        # الجلسة تدوم SESSION_LIFETIME_DAYS يوم حتى لو أغلق المستخدم المتصفح تماماً
        session.permanent = True
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


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE id = ?", (session["user_id"],)
        ).fetchone()

        if user is None:
            session.clear()
            return redirect(url_for("login"))

        if not check_password_hash(user["password_hash"], current_password):
            flash("كلمة المرور الحالية غير صحيحة.", "error")
            return redirect(url_for("change_password"))

        if len(new_password) < 4:
            flash("كلمة المرور الجديدة يجب أن تكون 4 أحرف على الأقل.", "error")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("كلمة المرور الجديدة وتأكيدها غير متطابقين.", "error")
            return redirect(url_for("change_password"))

        db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), user["id"]),
        )
        db.commit()
        flash("تم تغيير كلمة المرور بنجاح.", "success")

        if user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    return render_template("change_password.html")


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


@app.route("/api/log_calculation", methods=["POST"])
@login_required
def log_calculation():
    """يسجّل عملية حساب تعرفة لأغراض إحصائيات الأدمن (لا يؤثر على المستخدم إطلاقاً)."""
    db = get_db()
    db.execute(
        "INSERT INTO calculation_log (user_id, created_at) VALUES (?, ?)",
        (session.get("user_id"), datetime.now().strftime(DATE_FMT)),
    )
    db.commit()
    return {"ok": True}


@app.route("/api/favorites", methods=["GET"])
@login_required
def get_favorites():
    """يرجّع قائمة البنود المفضلة للمستخدم الحالي (أدمن أو مشترك) بصيغة JSON."""
    db = get_db()
    rows = db.execute(
        "SELECT hs_code, description, price FROM favorites WHERE user_id = ? ORDER BY added_at DESC",
        (session["user_id"],),
    ).fetchall()
    favorites = [
        {"hs_code": r["hs_code"], "description": r["description"], "price": r["price"]}
        for r in rows
    ]
    return jsonify(favorites)


@app.route("/api/favorites/toggle", methods=["POST"])
@login_required
def toggle_favorite():
    """يضيف أو يحذف صنف من قائمة المفضلة (نفس الطلب يبدّل الحالة تلقائياً)."""
    data = request.get_json(silent=True) or {}
    hs_code = (data.get("hs_code") or "").strip()
    description = (data.get("description") or "").strip()
    price = (data.get("price") or "").strip()

    if not hs_code:
        return jsonify({"error": "hs_code مطلوب"}), 400

    db = get_db()
    existing = db.execute(
        "SELECT id FROM favorites WHERE user_id = ? AND hs_code = ?",
        (session["user_id"], hs_code),
    ).fetchone()

    if existing:
        db.execute("DELETE FROM favorites WHERE id = ?", (existing["id"],))
        db.commit()
        return jsonify({"status": "removed", "hs_code": hs_code})

    db.execute(
        "INSERT INTO favorites (user_id, hs_code, description, price, added_at) VALUES (?, ?, ?, ?, ?)",
        (session["user_id"], hs_code, description, price, datetime.now().strftime(DATE_FMT)),
    )
    db.commit()
    return jsonify({"status": "added", "hs_code": hs_code})


# ---------------------------- لوحة الأدمن ----------------------------
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    rows = db.execute("SELECT * FROM users ORDER BY role DESC, id DESC").fetchall()

    users = []
    subscribers_count = 0
    active_count = 0
    expired_count = 0
    expiring_soon_count = 0

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

        if row["role"] != "admin":
            subscribers_count += 1
            if remaining < 0:
                expired_count += 1
            elif row["is_active"]:
                active_count += 1
                if remaining <= 7:
                    expiring_soon_count += 1

    today_str = datetime.now().strftime(DATE_FMT)
    total_calculations = db.execute(
        "SELECT COUNT(*) AS c FROM calculation_log"
    ).fetchone()["c"]
    calculations_today = db.execute(
        "SELECT COUNT(*) AS c FROM calculation_log WHERE created_at = ?", (today_str,)
    ).fetchone()["c"]

    stats = {
        "subscribers_count": subscribers_count,
        "active_count": active_count,
        "expired_count": expired_count,
        "expiring_soon_count": expiring_soon_count,
        "total_calculations": total_calculations,
        "calculations_today": calculations_today,
    }

    return render_template("admin_dashboard.html", users=users, stats=stats)


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


@app.route("/admin/renew_user/<int:user_id>", methods=["POST"])
@admin_required
def renew_user(user_id):
    """
    يجدد اشتراك المشترك: يعيد ضبط تاريخ البداية لليوم + المدة الجديدة المحددة،
    ويعيد تفعيل الحساب تلقائياً لو كان موقوفاً — بدون حذف الحساب أو فقدان
    اسم المستخدم/كلمة المرور.
    """
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if user is None or user["role"] == "admin":
        flash("لا يمكن تنفيذ هذا الإجراء.", "error")
        return redirect(url_for("admin_dashboard"))

    duration_days = request.form.get("renew_duration_days", "30")
    try:
        duration_days = int(duration_days)
        if duration_days < 1:
            raise ValueError
    except ValueError:
        flash("مدة التجديد يجب أن تكون رقماً صحيحاً أكبر من صفر.", "error")
        return redirect(url_for("admin_dashboard"))

    db.execute(
        "UPDATE users SET start_date = ?, duration_days = ?, is_active = 1 WHERE id = ?",
        (datetime.now().strftime(DATE_FMT), duration_days, user_id),
    )
    db.commit()
    flash(f"تم تجديد اشتراك '{user['username']}' لمدة {duration_days} يوم بدءاً من اليوم.", "success")
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
