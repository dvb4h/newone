/* الحفظ في المحفوظات (على السيرفر) من داخل الاستمارة. */
(function () {
  "use strict";
  const C = window.KASHF;
  const btn = document.getElementById("kSave");
  if (!C || !btn) return;
  const CUR = "kashf-doc:" + C.path;

  const getCur = () => { try { return JSON.parse(sessionStorage.getItem(CUR) || "null"); } catch (e) { return null; } };
  const setCur = (d) => { try { d ? sessionStorage.setItem(CUR, JSON.stringify(d)) : sessionStorage.removeItem(CUR); } catch (e) {} refreshBtn(); };
  function currentData() {
    try { if (typeof state !== "undefined" && state) return JSON.parse(JSON.stringify(state)); } catch (e) {}
    try { return JSON.parse(localStorage.getItem(C.key) || "{}") || {}; } catch (e) { return {}; }
  }
  // تُحفظ مربعات النص داخل بيانات الورقة تحت المفتاح __tb
  function payloadData() {
    try { if (window.KASHF_TB) window.KASHF_TB.flush(); } catch (e) {}
    const d = currentData();
    try { d.__tb = JSON.parse(localStorage.getItem(C.tbKey) || "[]") || []; } catch (e) { d.__tb = []; }
    return d;
  }
  function currentFs() { try { return JSON.parse(localStorage.getItem(C.fsKey) || "[]") || []; } catch (e) { return []; } }
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function suggestName() {
    const d = currentData();
    const parts = [d.material, d.declNo && "بيان " + d.declNo].filter((x) => x && String(x).trim());
    const now = new Date();
    parts.push(`${now.getDate()}-${now.getMonth() + 1}-${now.getFullYear()}`);
    return parts.join(" · ");
  }

  /* ---------- واجهة ---------- */
  const css = document.createElement("style");
  css.textContent = `
  .kdlg-bg{position:fixed;inset:0;z-index:10000;background:rgba(0,0,0,.55);backdrop-filter:blur(3px);display:grid;place-items:center;padding:16px;opacity:0;pointer-events:none;transition:opacity .15s}
  .kdlg-bg.on{opacity:1;pointer-events:auto}
  .kdlg{width:100%;max-width:420px;background:#15181e;border:1px solid rgba(255,255,255,.14);border-radius:16px;padding:20px;color:#eceef1;
    font:14px "IBM Plex Sans Arabic",Tahoma,sans-serif;direction:rtl;box-shadow:0 24px 60px rgba(0,0,0,.6);transform:translateY(8px) scale(.98);transition:transform .15s}
  .kdlg-bg.on .kdlg{transform:none}
  .kdlg h3{margin:0 0 4px;font-size:16px;font-weight:600}
  .kdlg .sub{color:#8a919a;font-size:12.5px;margin:0 0 16px}
  .kdlg .cur{background:rgba(212,165,78,.1);border:1px solid rgba(212,165,78,.3);border-radius:12px;padding:12px;margin-bottom:16px}
  .kdlg .cur small{display:block;color:#8a919a;font-size:12px;margin-bottom:8px}
  .kdlg .cur b{color:#f1cd85}
  .kdlg label{display:block;font-size:12.5px;color:#8a919a;margin:0 0 6px}
  .kdlg input{width:100%;box-sizing:border-box;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.14);border-radius:10px;padding:10px 12px;color:#eceef1;font:inherit;outline:none}
  .kdlg input:focus{border-color:#d4a54e;box-shadow:0 0 0 3px rgba(212,165,78,.18)}
  .kdlg .b{display:inline-flex;align-items:center;justify-content:center;gap:6px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.05);color:#eceef1;border-radius:10px;padding:9px 14px;cursor:pointer;font:inherit;font-size:13.5px;text-decoration:none}
  .kdlg .b:hover{background:rgba(255,255,255,.1)}
  .kdlg .b.gold{background:linear-gradient(180deg,#f1cd85,#d4a54e);color:#1a1305;border-color:transparent;font-weight:700}
  .kdlg .b:disabled{opacity:.6;cursor:wait}
  .kdlg .row{display:flex;gap:8px;margin-top:12px}
  .kdlg .row .b.gold{flex:1}
  .kdlg .err{color:#ff6b5b;font-size:12.5px;min-height:18px;margin-top:8px}
  .kdlg .foot{display:flex;justify-content:space-between;align-items:center;margin-top:14px;padding-top:14px;border-top:1px solid rgba(255,255,255,.08)}
  .kdlg .foot a{color:#f1cd85;font-size:13px;text-decoration:none}
  .ktoast{position:fixed;z-index:10001;left:50%;bottom:22px;transform:translateX(-50%) translateY(10px);opacity:0;transition:.2s;background:#15181e;border:1px solid rgba(65,207,143,.4);
    color:#eceef1;border-radius:999px;padding:9px 18px;font:13px "IBM Plex Sans Arabic",Tahoma,sans-serif;pointer-events:none;direction:rtl;white-space:nowrap}
  .ktoast.on{opacity:1;transform:translateX(-50%)}
  .ktoast.bad{border-color:rgba(255,107,91,.5)}
  #kSave.saved{border-color:rgba(212,165,78,.45)}
  @media print{.kdlg-bg,.ktoast{display:none!important}}`;
  document.head.appendChild(css);

  const bg = document.createElement("div");
  bg.className = "kdlg-bg";
  bg.innerHTML = `<div class="kdlg" role="dialog" aria-modal="true" aria-labelledby="kdlgT">
      <h3 id="kdlgT">حفظ في المحفوظات</h3>
      <p class="sub">تُحفظ الورقة على السيرفر وتقدر تفتحها من أي جهاز.</p>
      <div class="cur" hidden>
        <small>هذه الورقة مفتوحة من المحفوظات باسم <b class="cn"></b></small>
        <button type="button" class="b gold" data-a="update" style="width:100%">حفظ التعديلات عليها</button>
      </div>
      <label for="kName" class="nl">اسم الورقة</label>
      <input id="kName" maxlength="120" autocomplete="off">
      <div class="row">
        <button type="button" class="b gold" data-a="new">حفظ</button>
        <button type="button" class="b" data-a="close">إلغاء</button>
      </div>
      <div class="err"></div>
      <div class="foot"><a href="/archive">فتح المحفوظات ←</a><span style="color:#8a919a;font-size:12px">Ctrl + S</span></div>
    </div>`;
  document.body.appendChild(bg);
  const nameIn = bg.querySelector("#kName"), err = bg.querySelector(".err"), curBox = bg.querySelector(".cur");
  const newBtn = bg.querySelector('[data-a="new"]'), nl = bg.querySelector(".nl");

  const toast = document.createElement("div");
  toast.className = "ktoast";
  document.body.appendChild(toast);
  let toastT;
  function say(msg, bad) {
    toast.textContent = msg; toast.classList.toggle("bad", !!bad); toast.classList.add("on");
    clearTimeout(toastT); toastT = setTimeout(() => toast.classList.remove("on"), 2600);
  }

  function refreshBtn() {
    const cur = getCur();
    btn.classList.toggle("saved", !!cur);
    btn.title = cur ? `حفظ «${cur.name}» (Ctrl+S)` : "حفظ في المحفوظات (Ctrl+S)";
  }

  function open() {
    const cur = getCur();
    err.textContent = "";
    curBox.hidden = !cur;
    if (cur) {
      curBox.querySelector(".cn").textContent = "«" + cur.name + "»";
      nl.textContent = "أو احفظها كورقة جديدة باسم";
      newBtn.textContent = "حفظ كورقة جديدة";
      nameIn.value = "";
      nameIn.placeholder = suggestName();
    } else {
      nl.textContent = "اسم الورقة";
      newBtn.textContent = "حفظ";
      nameIn.value = suggestName();
      nameIn.placeholder = "مثال: غاز النيتروجين · الكويت";
    }
    bg.classList.add("on");
    setTimeout(() => { nameIn.focus(); nameIn.select(); }, 60);
  }
  const close = () => bg.classList.remove("on");

  async function send(url, body) {
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF": C.csrf },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
    let j = {};
    try { j = await r.json(); } catch (e) {}
    if (r.status === 401 || r.redirected) throw new Error("انتهت الجلسة، سجّل الدخول من جديد.");
    if (!r.ok) throw new Error(j.error || (r.status === 413 ? "الورقة كبيرة جداً." : "تعذّر الحفظ، حاول مرة ثانية."));
    return j;
  }
  function busy(on) { bg.querySelectorAll("button").forEach((b) => (b.disabled = on)); }

  async function saveNew() {
    const name = nameIn.value.trim() || nameIn.placeholder.trim();
    if (!name) { err.textContent = "اكتب اسماً للورقة."; nameIn.focus(); return; }
    busy(true); err.textContent = "";
    try {
      const j = await send("/api/docs", { form: C.form, name, data: payloadData(), fs: currentFs() });
      setCur({ id: j.id, name: j.name });
      close(); say(`حُفظت «${j.name}» في المحفوظات ✓`);
    } catch (e) { err.textContent = e.message; } finally { busy(false); }
  }
  async function saveUpdate(quiet) {
    const cur = getCur(); if (!cur) return open();
    busy(true); err.textContent = "";
    try {
      const j = await send("/api/docs/" + cur.id, { data: payloadData(), fs: currentFs() });
      setCur({ id: j.id, name: j.name });
      close(); say(`حُفظت التعديلات على «${j.name}» ✓`);
    } catch (e) {
      if (quiet) say(e.message, true); else err.textContent = e.message;
      if (/404/.test(e.message)) setCur(null);
    } finally { busy(false); }
  }

  btn.addEventListener("click", open);
  bg.addEventListener("click", (e) => {
    if (e.target === bg) return close();
    const a = e.target.closest("[data-a]"); if (!a) return;
    if (a.dataset.a === "close") close();
    else if (a.dataset.a === "new") saveNew();
    else if (a.dataset.a === "update") saveUpdate();
  });
  nameIn.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); saveNew(); } });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && bg.classList.contains("on")) close();
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      if (!bg.classList.contains("on")) open();
    }
  });
  // «شحنة جديدة» تبدأ ورقة جديدة غير مرتبطة بالمحفوظات
  // وزر «تراجع» يرجّع الارتباط بالورقة المحفوظة
  const clr = document.getElementById("clear"), undo = document.getElementById("undo");
  let lastCur = null;
  if (clr) clr.addEventListener("click", () => { lastCur = getCur(); setCur(null); });
  if (undo) undo.addEventListener("click", () => { if (lastCur) setCur(lastCur); lastCur = null; });

  refreshBtn();
})();
