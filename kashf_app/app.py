"""
منصة الكشف الكمركي — تطبيق اشتراكات مستقل
==========================================
Flask + قاعدة بيانات (PostgreSQL عبر DATABASE_URL، أو SQLite محلياً).

متغيرات البيئة:
    DATABASE_URL    رابط PostgreSQL (إن لم يُحدَّد تُستخدم SQLite محلية)
    SECRET_KEY      مفتاح تشفير الجلسات
    ADMIN_USERNAME  اسم مستخدم الأدمن عند أول تشغيل (الافتراضي admin)
    ADMIN_PASSWORD  كلمة مرور الأدمن عند أول تشغيل

تشغيل محلي:
    pip install -r requirements.txt
    ADMIN_PASSWORD=secret python app.py
"""

import os
import secrets
import sqlite3
from datetime import datetime, date, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, abort, Response,
)
from markupsafe import escape
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KASHF_HTML = os.path.join(BASE_DIR, "..", "kashf", "index.html")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
SQLITE_PATH = os.path.join(BASE_DIR, "kashf.db")
TZ = ZoneInfo("Asia/Baghdad")
DATE_FMT = "%Y-%m-%d"

if DATABASE_URL:
    import psycopg
    from psycopg.rows import dict_row

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    PERMANENT_SESSION_LIFETIME=timedelta(days=30),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(os.environ.get("RENDER")),
)


# ---------------------------------------------------------------- قاعدة البيانات
def get_db():
    if "db" not in g:
        if DATABASE_URL:
            g.db = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            g.db = sqlite3.connect(SQLITE_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def q(sql, args=(), one=False):
    if DATABASE_URL:
        sql = sql.replace("?", "%s")
    cur = get_db().execute(sql, args)
    if cur.description is None:
        return None
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def commit():
    get_db().commit()


def init_db():
    id_col = "SERIAL PRIMARY KEY" if DATABASE_URL else "INTEGER PRIMARY KEY AUTOINCREMENT"
    q(f"""CREATE TABLE IF NOT EXISTS users (
            id {id_col},
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            full_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            start_date TEXT,
            end_date TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            session_token TEXT,
            last_login TEXT,
            created_at TEXT
        )""")
    admin = q("SELECT id FROM users WHERE role = 'admin'", one=True)
    if admin is None:
        username = os.environ.get("ADMIN_USERNAME", "admin").strip() or "admin"
        password = os.environ.get("ADMIN_PASSWORD")
        if not password:
            password = secrets.token_urlsafe(9)
            print(f"[kashf] ADMIN_PASSWORD غير محدد — كلمة مرور مؤقتة للأدمن '{username}': {password}", flush=True)
        q("""INSERT INTO users (username, password_hash, role, created_at)
             VALUES (?, ?, 'admin', ?)""",
          (username, generate_password_hash(password), now_str()))
    commit()


# ---------------------------------------------------------------- أدوات
def today():
    return datetime.now(TZ).date()


def now_str():
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M")


def remaining_days(user):
    """عدد الأيام المتبقية (يوم الانتهاء نفسه محسوب). سالب = منتهي."""
    if not user["end_date"]:
        return -1
    end = datetime.strptime(user["end_date"], DATE_FMT).date()
    return (end - today()).days


def parse_days(value):
    try:
        days = int(value)
    except (TypeError, ValueError):
        return None
    return days if 1 <= days <= 3650 else None


def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def load_user_and_check():
    g.user = None
    if request.method == "POST" and request.endpoint != "login":
        if not session.get("csrf") or request.form.get("csrf") != session.get("csrf"):
            abort(400)

    uid = session.get("user_id")
    if uid is None:
        return
    user = q("SELECT * FROM users WHERE id = ?", (uid,), one=True)
    if user is None or user["session_token"] != session.get("token"):
        session.clear()
        if user is not None:
            flash("تم تسجيل الخروج لأن الحساب استُخدم من جهاز آخر.")
        return
    if user["role"] != "admin" and (not user["is_active"] or remaining_days(user) < 0):
        session.clear()
        flash("انتهى اشتراكك أو تم إيقاف حسابك. يرجى التواصل مع الإدارة.")
        return
    g.user = user


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if g.user is None:
            return redirect(url_for("login"))
        return view(*a, **kw)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if g.user is None:
            return redirect(url_for("login"))
        if g.user["role"] != "admin":
            abort(403)
        return view(*a, **kw)
    return wrapped


# ---------------------------------------------------------------- الدخول
@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = q("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("اسم المستخدم أو كلمة المرور غير صحيحة.")
            return redirect(url_for("login"))
        if user["role"] != "admin":
            if not user["is_active"]:
                flash("الحساب موقوف. يرجى التواصل مع الإدارة.")
                return redirect(url_for("login"))
            if remaining_days(user) < 0:
                flash("انتهت مدة اشتراكك. يرجى التواصل مع الإدارة للتجديد.")
                return redirect(url_for("login"))
        token = secrets.token_hex(16)
        q("UPDATE users SET session_token = ?, last_login = ? WHERE id = ?",
          (token, now_str(), user["id"]))
        commit()
        session.clear()
        session.permanent = True
        session["user_id"] = user["id"]
        session["token"] = token
        return redirect(url_for("admin") if user["role"] == "admin" else url_for("index"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current = request.form.get("current", "")
        new = request.form.get("new", "")
        if not check_password_hash(g.user["password_hash"], current):
            flash("كلمة المرور الحالية غير صحيحة.", "error")
        elif len(new) < 6:
            flash("كلمة المرور الجديدة يجب أن تكون 6 أحرف على الأقل.", "error")
        elif new != request.form.get("confirm", ""):
            flash("تأكيد كلمة المرور غير مطابق.", "error")
        else:
            q("UPDATE users SET password_hash = ? WHERE id = ?",
              (generate_password_hash(new), g.user["id"]))
            commit()
            flash("تم تغيير كلمة المرور.", "success")
            return redirect(url_for("admin") if g.user["role"] == "admin" else url_for("index"))
    return render_template("password.html")


# ---------------------------------------------------------------- منصة الكشف
_KASHF_CACHE = None


def kashf_html():
    global _KASHF_CACHE
    if _KASHF_CACHE is None:
        with open(KASHF_HTML, encoding="utf-8") as f:
            _KASHF_CACHE = f.read()
    return _KASHF_CACHE


@app.route("/")
@login_required
def index():
    u = g.user
    ic_user = ('<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/>'
               '<path d="M4 21a8 8 0 0 1 16 0"/></svg>')
    ic_out = ('<svg class="ic" viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>'
              '<path d="M10 17l-5-5 5-5M5 12h11"/></svg>')
    style = ('<style>.acct{text-decoration:none;color:inherit}'
             '@media (max-width:1000px){.acct .lbl{display:none}.acct{padding-inline:10px}}'
             '@media (max-width:520px){.top .chip,#print .lbl{display:none}}'
             '@media print{.acct{display:none!important}}</style>')
    if u["role"] == "admin":
        info = f'<a class="btn acct" href="/admin" title="لوحة الأدمن">{ic_user}<span class="lbl">لوحة الأدمن</span></a>'
    else:
        days = remaining_days(u)
        color = "#ff6b5b" if days <= 3 else ("#f1cd85" if days <= 7 else "#41cf8f")
        label = "ينتهي اليوم" if days == 0 else f"متبقٍ {days} يوم"
        info = (f'<span class="btn acct" title="{escape(u["username"])} · {label} · ينتهي في {escape(u["end_date"])}" '
                f'style="cursor:default;color:{color}">{ic_user}'
                f'<span class="lbl" style="color:var(--text)">{escape(u["username"])} · {label}</span></span>')
    bar = (f'{style}{info}<a class="btn acct" href="/logout" title="تسجيل الخروج">{ic_out}'
           f'<span class="lbl">خروج</span></a></header>')
    html = kashf_html().replace("</header>", bar, 1)
    resp = Response(html, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------- لوحة الأدمن
@app.route("/admin")
@admin_required
def admin():
    rows = q("SELECT * FROM users WHERE role = 'user' ORDER BY id DESC")
    users, stats = [], {"total": 0, "active": 0, "expiring": 0, "expired": 0, "stopped": 0}
    for r in rows:
        days = remaining_days(r)
        if not r["is_active"]:
            status = "stopped"
        elif days < 0:
            status = "expired"
        elif days <= 7:
            status = "expiring"
        else:
            status = "active"
        stats["total"] += 1
        stats[status] += 1
        if status == "expiring":
            stats["active"] += 1
        users.append({**dict(r), "days": days, "status": status})
    query = request.args.get("q", "").strip()
    if query:
        users = [u for u in users if query in u["username"] or query in (u["full_name"] or "")
                 or query in (u["phone"] or "")]
    return render_template("admin.html", users=users, stats=stats, query=query)


@app.route("/admin/add", methods=["POST"])
@admin_required
def admin_add():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    days = parse_days(request.form.get("days"))
    if not username or not password:
        flash("اسم المستخدم وكلمة المرور مطلوبان.", "error")
    elif len(password) < 4:
        flash("كلمة المرور يجب أن تكون 4 أحرف على الأقل.", "error")
    elif days is None:
        flash("مدة الاشتراك يجب أن تكون رقماً بين 1 و 3650 يوماً.", "error")
    elif q("SELECT id FROM users WHERE username = ?", (username,), one=True):
        flash("اسم المستخدم موجود مسبقاً.", "error")
    else:
        start = today()
        end = start + timedelta(days=days - 1)
        q("""INSERT INTO users (username, password_hash, role, full_name, phone, notes,
                                start_date, end_date, is_active, created_at)
             VALUES (?, ?, 'user', ?, ?, ?, ?, ?, 1, ?)""",
          (username, generate_password_hash(password),
           request.form.get("full_name", "").strip(), request.form.get("phone", "").strip(),
           request.form.get("notes", "").strip(),
           start.strftime(DATE_FMT), end.strftime(DATE_FMT), now_str()))
        commit()
        flash(f"تمت إضافة المشترك «{username}» لمدة {days} يوم (حتى {end.strftime(DATE_FMT)}).", "success")
    return redirect(url_for("admin"))


def get_subscriber(uid):
    u = q("SELECT * FROM users WHERE id = ? AND role = 'user'", (uid,), one=True)
    if u is None:
        abort(404)
    return u


@app.route("/admin/renew/<int:uid>", methods=["POST"])
@admin_required
def admin_renew(uid):
    u = get_subscriber(uid)
    days = parse_days(request.form.get("days"))
    if days is None:
        flash("عدد الأيام غير صالح.", "error")
        return redirect(url_for("admin"))
    # التجديد يُضاف إلى نهاية الاشتراك الحالي إن كان سارياً، وإلا يبدأ من اليوم
    if remaining_days(u) >= 0:
        base = datetime.strptime(u["end_date"], DATE_FMT).date()
        end = base + timedelta(days=days)
    else:
        end = today() + timedelta(days=days - 1)
        q("UPDATE users SET start_date = ? WHERE id = ?", (today().strftime(DATE_FMT), uid))
    q("UPDATE users SET end_date = ? WHERE id = ?", (end.strftime(DATE_FMT), uid))
    commit()
    flash(f"تم تجديد اشتراك «{u['username']}» حتى {end.strftime(DATE_FMT)}.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/toggle/<int:uid>", methods=["POST"])
@admin_required
def admin_toggle(uid):
    u = get_subscriber(uid)
    q("UPDATE users SET is_active = ? WHERE id = ?", (0 if u["is_active"] else 1, uid))
    commit()
    flash(f"تم {'إيقاف' if u['is_active'] else 'تفعيل'} حساب «{u['username']}».", "success")
    return redirect(url_for("admin"))


@app.route("/admin/password/<int:uid>", methods=["POST"])
@admin_required
def admin_password(uid):
    u = get_subscriber(uid)
    new = request.form.get("password", "")
    if len(new) < 4:
        flash("كلمة المرور يجب أن تكون 4 أحرف على الأقل.", "error")
    else:
        q("UPDATE users SET password_hash = ?, session_token = NULL WHERE id = ?",
          (generate_password_hash(new), uid))
        commit()
        flash(f"تم تغيير كلمة مرور «{u['username']}».", "success")
    return redirect(url_for("admin"))


@app.route("/admin/kick/<int:uid>", methods=["POST"])
@admin_required
def admin_kick(uid):
    u = get_subscriber(uid)
    q("UPDATE users SET session_token = NULL WHERE id = ?", (uid,))
    commit()
    flash(f"تم تسجيل خروج «{u['username']}» من جميع الأجهزة.", "success")
    return redirect(url_for("admin"))


@app.route("/admin/delete/<int:uid>", methods=["POST"])
@admin_required
def admin_delete(uid):
    u = get_subscriber(uid)
    q("DELETE FROM users WHERE id = ?", (uid,))
    commit()
    flash(f"تم حذف المشترك «{u['username']}».", "success")
    return redirect(url_for("admin"))


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
