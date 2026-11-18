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
import re
import json
import secrets
import sqlite3
from datetime import datetime, date, timedelta
from functools import wraps
from zoneinfo import ZoneInfo

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, abort, Response, jsonify,
)
from markupsafe import escape
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KASHF_DIR = os.path.join(BASE_DIR, "forms")
# الاستمارات المتاحة: (المسار، اسم الملف، الاسم المعروض)
# (المسار، اسم الملف، الاسم المعروض، مفتاح حفظ بيانات الاستمارة في المتصفح)
FORMS = [
    ("/", "index.html", "استمارة الكشف", "customs-form-v2"),
    ("/form2", "form2.html", "استمارة كشف نموذج 2", "customs-form-model2-v1"),
]
MAX_DOC_BYTES = 300_000      # حد حجم الورقة المحفوظة الواحدة
MAX_DOCS_PER_USER = 3000
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
    q(f"""CREATE TABLE IF NOT EXISTS saved_docs (
            id {id_col},
            user_id INTEGER NOT NULL,
            form INTEGER NOT NULL,
            name TEXT NOT NULL,
            data TEXT NOT NULL,
            fontsizes TEXT NOT NULL DEFAULT '[]',
            created_at TEXT,
            updated_at TEXT
        )""")
    q("CREATE INDEX IF NOT EXISTS idx_saved_docs_user ON saved_docs (user_id)")
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
        sent = request.headers.get("X-CSRF") or request.form.get("csrf")
        if not session.get("csrf") or sent != session.get("csrf"):
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
_HTML_CACHE = {}


def static_ver(name):
    """رقم إصدار للملفات الثابتة حتى يحمّل المتصفح النسخة الجديدة بعد كل تعديل."""
    try:
        return int(os.path.getmtime(os.path.join(BASE_DIR, "static", name)))
    except OSError:
        return 0


FS_VER = static_ver("fontsize.js")
ARCH_VER = static_ver("archive.js")
IC_FOLDER = ('<svg class="ic" viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5'
             'a2 2 0 0 1-2-2z"/></svg>')
IC_SAVE = ('<svg class="ic" viewBox="0 0 24 24"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>'
           '<path d="M17 21v-8H7v8M7 3v5h8"/></svg>')


def script_json(obj):
    """JSON آمن للتضمين داخل وسم <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/").replace("\u2028", "\\u2028")


CRUMB_RE = re.compile(r'<div class="crumb">.*?</div>', re.S)


def form_html(filename):
    if filename not in _HTML_CACHE:
        with open(os.path.join(KASHF_DIR, filename), encoding="utf-8") as f:
            _HTML_CACHE[filename] = f.read()
    return _HTML_CACHE[filename]


@app.route("/")
@login_required
def index():
    return render_form(0)


@app.route("/form2")
@login_required
def form2():
    return render_form(1)


def render_form(idx):
    form_path, filename, _, form_key = FORMS[idx]
    u = g.user

    # فتح ورقة من المحفوظات: ?doc=<id>
    doc = None
    doc_id = request.args.get("doc", type=int)
    if doc_id:
        row = q("SELECT * FROM saved_docs WHERE id = ? AND user_id = ?", (doc_id, u["id"]), one=True)
        if row is None:
            flash("الورقة غير موجودة في محفوظاتك.", "error")
            return redirect(url_for("archive"))
        if row["form"] != idx + 1:
            return redirect(f'{FORMS[row["form"] - 1][0]}?doc={doc_id}')
        doc = {"id": row["id"], "name": row["name"],
               "data": json.loads(row["data"]), "fs": json.loads(row["fontsizes"] or "[]")}
    cfg = {"form": idx + 1, "path": form_path, "key": form_key,
           "fsKey": "kashf-fontsizes:" + form_path, "csrf": csrf_token(), "doc": doc}
    preload = (
        "<script>(function(){var C=window.KASHF=" + script_json(cfg) + ";"
        "var cur='kashf-doc:'+C.path;"
        "try{if(C.doc){localStorage.setItem(C.key,JSON.stringify(C.doc.data));"
        "localStorage.setItem(C.fsKey,JSON.stringify(C.doc.fs||[]));"
        "sessionStorage.setItem(cur,JSON.stringify({id:C.doc.id,name:C.doc.name}));"
        "history.replaceState(null,'',C.path);}}catch(e){}"
        "delete C.doc;})();</script>"
    )
    ic_user = ('<svg class="ic" viewBox="0 0 24 24"><circle cx="12" cy="8" r="4"/>'
               '<path d="M4 21a8 8 0 0 1 16 0"/></svg>')
    ic_out = ('<svg class="ic" viewBox="0 0 24 24"><path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>'
              '<path d="M10 17l-5-5 5-5M5 12h11"/></svg>')
    style = ('<style>.acct{text-decoration:none;color:inherit}'
             '@media (max-width:1500px){.acct.ico .lbl,.top .chip .pg,.top .chip .sep,#print kbd,.forms .la{display:none}'
             '.acct.ico{padding-inline:10px}}'
             '@media (max-width:1000px){.acct .lbl{display:none}.acct{padding-inline:10px}}'
             '@media (max-width:520px){.top .chip,#print .lbl{display:none}}'
             '@media print{.acct{display:none!important}}</style>')
    if u["role"] == "admin":
        info = f'<a class="btn acct ico" href="/admin" title="لوحة الأدمن">{ic_user}<span class="lbl">لوحة الأدمن</span></a>'
    else:
        days = remaining_days(u)
        color = "#ff6b5b" if days <= 3 else ("#f1cd85" if days <= 7 else "#41cf8f")
        label = "ينتهي اليوم" if days == 0 else f"متبقٍ {days} يوم"
        info = (f'<span class="btn acct" title="{escape(u["username"])} · {label} · ينتهي في {escape(u["end_date"])}" '
                f'style="cursor:default;color:{color}">{ic_user}'
                f'<span class="lbl" style="color:var(--text)">{escape(u["username"])} · {label}</span></span>')
    save_btn = (f'<button class="btn acct ico" id="kSave" type="button" title="حفظ في المحفوظات (Ctrl+S)">'
                f'{IC_SAVE}<span class="lbl">حفظ</span></button>')
    bar = (f'{style}{save_btn}{info}<a class="btn acct ico" href="/logout" title="تسجيل الخروج">{ic_out}'
           f'<span class="lbl">خروج</span></a></header>')
    tabs = "".join(
        f'<a href="{p}"{on}><span class="lf">{escape(name)}</span>'
        f'<span class="ls">نموذج {i + 1}</span></a>'
        for i, (p, _, name, _k) in enumerate(FORMS)
        for on in [' class="on"' if i == idx else ""]
    ) + (f'<a href="/archive" class="arch" title="المحفوظات">{IC_FOLDER}'
         f'<span class="la">المحفوظات</span></a>')
    tabs_html = (
        '<style>.forms{display:flex;gap:3px;padding:3px;border:1px solid var(--line2);border-radius:11px;'
        'background:rgba(0,0,0,.25);margin-inline-start:6px}'
        '.forms a{padding:6px 12px;border-radius:8px;font-size:13px;color:var(--muted);text-decoration:none;'
        'white-space:nowrap;transition:background .15s,color .15s}'
        '.forms a:hover{color:var(--text)}'
        '.forms a.on{background:var(--gold-soft);color:var(--gold2);font-weight:600}'
        '.forms .ls{display:none}'
        '.forms .arch{display:flex;align-items:center;gap:6px;border-inline-start:1px solid var(--line2);'
        'border-radius:0 8px 8px 0;margin-inline-start:2px}'
        '.forms .arch .ic{width:16px;height:16px}'
        '@media (max-width:700px){.forms .la{display:none}}'
        '@media (max-width:1400px){.forms .lf{display:none}.forms .ls{display:inline}}'
        '.top .btn{white-space:nowrap}'
        '@media (max-width:560px){.top .brand .t{display:none}.forms a{padding:6px 8px;font-size:12px}}'
        '@media print{.forms{display:none!important}}</style>'
        f'<nav class="forms" aria-label="الاستمارات">{tabs}</nav>'
    )
    html = form_html(filename)
    html = CRUMB_RE.sub(lambda m: tabs_html, html, count=1)
    html = html.replace("</header>", bar, 1)
    html = html.replace("<body>", "<body>" + preload, 1)
    html = html.replace("</body>", f'<script src="/static/fontsize.js?v={FS_VER}"></script>'
                                   f'<script src="/static/archive.js?v={ARCH_VER}"></script></body>', 1)
    resp = Response(html, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------- المحفوظات
def doc_summary(data):
    """سطر مختصر يعرّف الورقة في قائمة المحفوظات."""
    try:
        d = json.loads(data)
    except ValueError:
        return ""
    parts = [d.get("material"), d.get("company"), d.get("declNo") and f"بيان {d.get('declNo')}"]
    return " · ".join(str(p).strip() for p in parts if p and str(p).strip())


@app.route("/archive")
@login_required
def archive():
    rows = q("""SELECT id, form, name, data, created_at, updated_at FROM saved_docs
                WHERE user_id = ? ORDER BY updated_at DESC, id DESC""", (g.user["id"],))
    docs = [{"id": r["id"], "form": r["form"], "name": r["name"], "summary": doc_summary(r["data"]),
             "created_at": r["created_at"], "updated_at": r["updated_at"],
             "url": f'{FORMS[r["form"] - 1][0]}?doc={r["id"]}' if 1 <= r["form"] <= len(FORMS) else "#"}
            for r in rows]
    forms = [{"n": i + 1, "path": p, "name": name} for i, (p, _, name, _k) in enumerate(FORMS)]
    return render_template("archive.html", docs=docs, forms=forms)


def clean_name(value):
    return " ".join(str(value or "").split())[:120]


def doc_payload():
    body = request.get_json(silent=True) or {}
    data = body.get("data")
    fs = body.get("fs") or []
    if not isinstance(data, dict) or not isinstance(fs, list):
        abort(400)
    data_s, fs_s = json.dumps(data, ensure_ascii=False), json.dumps(fs, ensure_ascii=False)
    if len(data_s) + len(fs_s) > MAX_DOC_BYTES:
        abort(413)
    return body, data_s, fs_s


@app.route("/api/docs", methods=["POST"])
@login_required
def api_doc_create():
    body, data_s, fs_s = doc_payload()
    name = clean_name(body.get("name"))
    try:
        form = int(body.get("form"))
    except (TypeError, ValueError):
        form = 0
    if not name:
        return jsonify(error="اكتب اسماً للورقة."), 400
    if not 1 <= form <= len(FORMS):
        abort(400)
    count = q("SELECT COUNT(*) AS c FROM saved_docs WHERE user_id = ?", (g.user["id"],), one=True)["c"]
    if count >= MAX_DOCS_PER_USER:
        return jsonify(error="وصلت للحد الأقصى من المحفوظات. احذف أوراقاً قديمة أولاً."), 400
    now = now_str()
    row = q("""INSERT INTO saved_docs (user_id, form, name, data, fontsizes, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id""",
            (g.user["id"], form, name, data_s, fs_s, now, now), one=True)
    commit()
    return jsonify(id=row["id"], name=name, updated_at=now)


def own_doc(doc_id):
    row = q("SELECT * FROM saved_docs WHERE id = ? AND user_id = ?", (doc_id, g.user["id"]), one=True)
    if row is None:
        abort(404)
    return row


@app.route("/api/docs/<int:doc_id>", methods=["POST"])
@login_required
def api_doc_update(doc_id):
    row = own_doc(doc_id)
    body, data_s, fs_s = doc_payload()
    name = clean_name(body.get("name")) or row["name"]
    now = now_str()
    q("UPDATE saved_docs SET data = ?, fontsizes = ?, name = ?, updated_at = ? WHERE id = ?",
      (data_s, fs_s, name, now, doc_id))
    commit()
    return jsonify(id=doc_id, name=name, updated_at=now)


@app.route("/archive/<int:doc_id>/rename", methods=["POST"])
@login_required
def archive_rename(doc_id):
    own_doc(doc_id)
    name = clean_name(request.form.get("name"))
    if not name:
        flash("الاسم لا يمكن أن يكون فارغاً.", "error")
    else:
        q("UPDATE saved_docs SET name = ? WHERE id = ?", (name, doc_id))
        commit()
        flash(f"تمت إعادة التسمية إلى «{name}».", "success")
    return redirect(url_for("archive"))


@app.route("/archive/<int:doc_id>/delete", methods=["POST"])
@login_required
def archive_delete(doc_id):
    row = own_doc(doc_id)
    q("DELETE FROM saved_docs WHERE id = ?", (doc_id,))
    commit()
    flash(f"تم حذف «{row['name']}» من المحفوظات.", "success")
    return redirect(url_for("archive"))


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
    q("DELETE FROM saved_docs WHERE user_id = ?", (uid,))
    q("DELETE FROM users WHERE id = ?", (uid,))
    commit()
    flash(f"تم حذف المشترك «{u['username']}».", "success")
    return redirect(url_for("admin"))


with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
