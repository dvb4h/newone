/* مربعات نص حرّة فوق ورقة الاستمارة: إضافة، كتابة، سحب، تكبير/تصغير، حذف.
   تُحفظ في المتصفح لكل استمارة (ومع الورقة في المحفوظات) وتظهر في الطباعة. */
(function () {
  "use strict";
  // كل أوراق الاستمارة (الوجه، والظهر إن وُجد). لكل مربع رقم ورقته pg
  const sheets = [...document.querySelectorAll(".paper")];
  if (!sheets.length) return;
  const sheetOfBox = (b) => sheets[b.pg || 0] || sheets[0];
  const visibleSheet = () => sheets.find((s) => !s.classList.contains("off")) || sheets[0];
  const STORE = "kashf-textboxes:" + location.pathname;
  const MIN_W = 40, MIN_H = 22, DEF_SIZE = 14;
  const PLAIN = (() => { const d = document.createElement("div"); d.contentEditable = "plaintext-only"; return d.contentEditable === "plaintext-only"; })();

  let boxes = [];
  try { boxes = JSON.parse(localStorage.getItem(STORE) || "[]"); } catch (e) { boxes = []; }
  if (!Array.isArray(boxes)) boxes = [];
  let saveT;
  const save = () => { clearTimeout(saveT); saveT = setTimeout(() => { try { localStorage.setItem(STORE, JSON.stringify(boxes)); } catch (e) {} }, 150); };
  const saveNow = () => { clearTimeout(saveT); try { localStorage.setItem(STORE, JSON.stringify(boxes)); } catch (e) {} };
  addEventListener("pagehide", saveNow);

  /* ---------- أدوات القياس (الورقة مكبّرة/مصغّرة بـ transform) ---------- */
  function untilt() { try { if (typeof resetTilt === "function") resetTilt(); } catch (e) {} }
  function scale(sh) { sh = sh || visibleSheet(); const r = sh.getBoundingClientRect(); return r.width / sh.offsetWidth || 1; }
  function toPaper(sh, clientX, clientY) {
    const r = sh.getBoundingClientRect(), s = scale(sh);
    return { x: (clientX - r.left) / s, y: (clientY - r.top) / s };
  }
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  function fit(b) {
    const sh = sheetOfBox(b), W = sh.clientWidth, H = sh.clientHeight;
    b.w = clamp(b.w, MIN_W, W); b.h = clamp(b.h, MIN_H, H);
    b.x = clamp(b.x, 0, W - b.w); b.y = clamp(b.y, 0, H - b.h);
  }

  /* ---------- الأنماط ---------- */
  const css = document.createElement("style");
  css.textContent = `
  .tb{position:absolute;z-index:6;box-sizing:border-box;border:1px dashed transparent;border-radius:2px;color:#000;direction:rtl;touch-action:none}
  .tb:hover{border-color:rgba(29,78,216,.45)}
  .tb.sel{border:1px dashed #1d4ed8;background:rgba(29,78,216,.03)}
  .tb .tb-t{width:100%;height:100%;box-sizing:border-box;padding:3px 5px;outline:none;white-space:pre-wrap;overflow-wrap:anywhere;overflow:hidden;
    line-height:1.45;font-family:inherit;font-weight:600;cursor:text;-webkit-user-select:text;user-select:text;touch-action:auto}
  .tb .tb-t:empty::before{content:"اكتب هنا…";color:#9ca3af;font-weight:400}
  .tb .tb-ui{display:none}
  .tb.sel .tb-ui{display:block}
  .tb .tb-bar{position:absolute;bottom:100%;right:-1px;margin-bottom:2px;display:flex;gap:3px;transform:scale(var(--tbs,1));transform-origin:100% 100%}
  .tb .tb-mv{height:22px;padding:0 8px;border-radius:6px 6px 0 0;background:#1d4ed8;color:#fff;
    font:600 11px "IBM Plex Sans Arabic",Tahoma,sans-serif;display:flex;align-items:center;gap:5px;cursor:move;white-space:nowrap;user-select:none;-webkit-user-select:none}
  .tb .tb-mv svg{width:13px;height:13px;stroke:currentColor;fill:none;stroke-width:2}
  .tb .tb-x{width:22px;height:22px;border-radius:6px 6px 0 0;background:#b91c1c;color:#fff;border:0;
    display:grid;place-items:center;cursor:pointer;padding:0;font:700 14px/1 Tahoma,sans-serif}
  .tb .tb-r{position:absolute;width:12px;height:12px;transform:scale(var(--tbs,1));background:#fff;border:2px solid #1d4ed8;border-radius:3px;bottom:-7px}
  .tb .tb-r.l{left:-7px;cursor:nesw-resize}
  .tb .tb-r.r{right:-7px;cursor:nwse-resize}
  .tb.drag,.tb.drag *{cursor:move!important}
  @media (pointer:coarse){
    .tb .tb-mv{height:32px;font-size:12.5px;padding:0 12px}
    .tb .tb-x{width:32px;height:32px;font-size:18px}
    .tb .tb-r{width:20px;height:20px;bottom:-11px}
    .tb .tb-r.l{left:-11px}.tb .tb-r.r{right:-11px}
  }
  .tb-add-menu{position:fixed;z-index:9999;background:#15181e;border:1px solid rgba(255,255,255,.14);border-radius:12px;padding:6px;box-shadow:0 18px 50px rgba(0,0,0,.55);direction:rtl}
  .tb-add-menu button{display:flex;align-items:center;gap:8px;width:100%;border:0;background:none;color:#eceef1;font:13px "IBM Plex Sans Arabic",Tahoma,sans-serif;padding:8px 12px;border-radius:8px;cursor:pointer;white-space:nowrap}
  .tb-add-menu button:hover{background:rgba(255,255,255,.08)}
  .tb-add-menu svg,.dock #tbAdd svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
  #tbFab{display:none;position:fixed;z-index:20;left:16px;bottom:92px;height:44px;padding:0 14px;border-radius:12px;border:1px solid rgba(212,165,78,.45);
    background:rgba(18,20,25,.9);backdrop-filter:blur(14px);color:#f1cd85;font:600 13px "IBM Plex Sans Arabic",Tahoma,sans-serif;align-items:center;gap:7px;
    box-shadow:0 12px 30px rgba(0,0,0,.5)}
  #tbFab svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
  @media (max-width:1000px){body.m-prev #tbFab{display:flex}}
  @media print{
    #tbFab{display:none!important}
    .tb,.tb.sel,.tb:hover{border-color:transparent!important;background:none!important}
    .tb .tb-ui,.tb-add-menu{display:none!important}
    .tb .tb-t:empty::before{content:none}
  }`;
  document.head.appendChild(css);

  const IC_T = '<svg viewBox="0 0 24 24"><path d="M4 7V5h16v2M9 19h6M12 5v14"/><rect x="2" y="2" width="20" height="20" rx="3" stroke-dasharray="3 3" opacity=".6"/></svg>';
  const IC_MOVE = '<svg viewBox="0 0 24 24"><path d="M12 2v20M2 12h20M12 2l-3 3M12 2l3 3M12 22l-3-3M12 22l3-3M2 12l3-3M2 12l3 3M22 12l-3-3M22 12l-3 3"/></svg>';

  /* ---------- رسم المربعات ---------- */
  let selected = null;
  const byId = (id) => boxes.find((b) => b.id === id);
  function render(b) {
    let el = document.querySelector(`.paper .tb[data-id="${b.id}"]`);
    if (!el) {
      el = document.createElement("div");
      el.className = "tb";
      el.dataset.id = b.id;
      el.innerHTML = `<div class="tb-t" dir="auto"></div>
        <div class="tb-ui"><div class="tb-bar"><div class="tb-mv" title="اسحب لتحريك المربع">${IC_MOVE}<span>اسحب للتحريك</span></div>
        <button type="button" class="tb-x" title="حذف المربع">×</button></div>
        <span class="tb-r l" data-dir="l" title="تكبير/تصغير"></span><span class="tb-r r" data-dir="r" title="تكبير/تصغير"></span></div>`;
      const t = el.querySelector(".tb-t");
      t.contentEditable = PLAIN ? "plaintext-only" : "true";
      t.textContent = b.text || "";
      sheetOfBox(b).appendChild(el);
    }
    el.style.left = b.x + "px"; el.style.top = b.y + "px";
    el.style.width = b.w + "px"; el.style.height = b.h + "px";
    const t = el.querySelector(".tb-t");
    t.style.fontSize = (b.size || DEF_SIZE) + "px";
    t.style.color = b.color || "";
    return el;
  }
  function syncScale() { const v = (1 / scale()).toFixed(3); sheets.forEach((s) => s.style.setProperty("--tbs", v)); }
  addEventListener("resize", () => setTimeout(syncScale, 50));
  ["zIn", "zOut", "zFit"].forEach((id) => { const b = document.getElementById(id); if (b) b.addEventListener("click", () => setTimeout(syncScale, 50)); });
  function select(el) {
    if (el) syncScale();
    if (selected === el) return;
    if (selected) selected.classList.remove("sel");
    selected = el;
    if (el) el.classList.add("sel");
  }
  function remove(el) {
    const id = el.dataset.id;
    boxes = boxes.filter((b) => b.id !== id);
    if (selected === el) selected = null;
    el.remove();
    saveNow();
  }
  function add(sh, x, y) {
    const pg = Math.max(0, sheets.indexOf(sh));
    const b = { id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6), x: x - 90, y: y - 14, w: 180, h: 34, text: "", size: DEF_SIZE };
    if (pg) b.pg = pg;
    fit(b);
    boxes.push(b);
    const el = render(b);
    select(el);
    saveNow();
    el.querySelector(".tb-t").focus({ preventScroll: true });
    return el;
  }
  function addVisible() {
    // في منتصف الجزء الظاهر من الورقة
    untilt();
    const paper = visibleSheet();
    const r = paper.getBoundingClientRect();
    const desk = document.getElementById("desk");
    const d = desk ? desk.getBoundingClientRect() : { left: 0, top: 0, right: innerWidth, bottom: innerHeight };
    const cx = (Math.max(r.left, d.left) + Math.min(r.right, d.right)) / 2;
    const cy = (Math.max(r.top, d.top) + Math.min(r.bottom, d.bottom, innerHeight)) / 2;
    const p = toPaper(paper, cx, cy);
    if (document.body.classList.contains("m-prev") === false && matchMedia("(max-width:1000px)").matches && typeof setView === "function") {
      try { setView("prev"); } catch (e) {}
    }
    return add(paper, p.x, p.y);
  }

  /* ---------- الكتابة ---------- */
  const onInput = (e) => {
    const t = e.target.closest && e.target.closest(".tb-t"); if (!t) return;
    const b = byId(t.parentElement.dataset.id); if (!b) return;
    b.text = t.innerText.replace(/\n$/, "");
    // كبّر المربع تلقائياً إذا تجاوز النص ارتفاعه
    if (t.scrollHeight > t.clientHeight + 1) { b.h = Math.min(sheetOfBox(b).clientHeight - b.y, t.scrollHeight + 2); render(b); }
    save();
  };
  sheets.forEach((sh) => sh.addEventListener("input", onInput));
  if (!PLAIN) {
    sheets.forEach((sh) => sh.addEventListener("paste", (e) => {
      if (!e.target.closest || !e.target.closest(".tb-t")) return;
      e.preventDefault();
      document.execCommand("insertText", false, (e.clipboardData || window.clipboardData).getData("text"));
    }));
  }

  /* ---------- السحب وتغيير الحجم ---------- */
  let op = null;
  const onDown = (e) => {
    const el = e.target.closest && e.target.closest(".tb");
    if (!el) { if (selected && !e.target.closest(".tb")) select(null); return; }
    select(el);
    if (e.target.closest(".tb-x")) { e.preventDefault(); remove(el); return; }
    const handle = e.target.closest(".tb-r");
    const onMove = e.target.closest(".tb-mv");
    const onEdge = e.target === el;             // حافة المربع (خارج منطقة الكتابة)
    if (!handle && !onMove && !onEdge) return;  // نقر داخل النص = كتابة عادية
    e.preventDefault();
    untilt();
    const b = byId(el.dataset.id);
    op = { el, b, mode: handle ? handle.dataset.dir : "move", sx: e.clientX, sy: e.clientY, s: scale(sheetOfBox(b)), o: { ...b }, id: e.pointerId };
    el.classList.add("drag");
    try { el.setPointerCapture(e.pointerId); } catch (err) {}
  };
  sheets.forEach((sh) => sh.addEventListener("pointerdown", onDown));
  // في مرحلة الالتقاط حتى لا يتحرك منظور الورقة ثلاثي الأبعاد أثناء السحب
  addEventListener("pointermove", (e) => {
    if (!op) return;
    e.stopPropagation();
    const dx = (e.clientX - op.sx) / op.s, dy = (e.clientY - op.sy) / op.s, b = op.b, o = op.o;
    if (op.mode === "move") { b.x = o.x + dx; b.y = o.y + dy; }
    else {
      b.h = Math.max(MIN_H, o.h + dy);
      if (op.mode === "r") b.w = Math.max(MIN_W, o.w + dx);                       // الزاوية اليمنى: الحافة اليسرى ثابتة
      else { b.w = Math.max(MIN_W, o.w - dx); b.x = o.x + o.w - b.w; }            // الزاوية اليسرى: الحافة اليمنى ثابتة
    }
    fit(b);
    render(b);
  }, true);
  function endOp() {
    if (!op) return;
    op.el.classList.remove("drag");
    op = null;
    saveNow();
  }
  addEventListener("pointerup", endOp, true);
  addEventListener("pointercancel", endOp, true);
  document.addEventListener("pointerdown", (e) => { if (selected && !e.target.closest(".paper,.fsm,.tb-add-menu")) select(null); });
  document.addEventListener("keydown", (e) => {
    if (!selected) return;
    const editing = document.activeElement && document.activeElement.closest && document.activeElement.closest(".tb-t");
    if (e.key === "Escape") { if (editing) document.activeElement.blur(); select(null); return; }
    if (editing) return;
    const b = byId(selected.dataset.id); if (!b) return;
    if (e.key === "Delete") { e.preventDefault(); remove(selected); return; }
    const step = e.shiftKey ? 10 : 1, mv = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] }[e.key];
    if (mv) { e.preventDefault(); b.x += mv[0]; b.y += mv[1]; fit(b); render(b); save(); }
  });

  /* ---------- زر الإضافة + قائمة كلك يمين على مكان فارغ ---------- */
  const dock = document.getElementById("dock");
  if (dock) {
    const sep = document.createElement("span"); sep.className = "div";
    const btn = document.createElement("button");
    btn.type = "button"; btn.id = "tbAdd"; btn.title = "إضافة مربع نص";
    btn.innerHTML = IC_T;
    btn.addEventListener("click", addVisible);
    dock.append(sep, btn);
  }
  // على الهاتف شريط التكبير مخفي، فنضيف زراً عائماً في وضع المعاينة
  const fab = document.createElement("button");
  fab.type = "button"; fab.id = "tbFab";
  fab.innerHTML = IC_T + "<span>مربع نص</span>";
  fab.addEventListener("click", addVisible);
  document.body.appendChild(fab);
  const addMenu = document.createElement("div");
  addMenu.className = "tb-add-menu"; addMenu.hidden = true;
  addMenu.innerHTML = `<button type="button">${IC_T}إضافة مربع نص هنا</button>`;
  document.body.appendChild(addMenu);
  let addAt = null, addSheet = null;
  addMenu.querySelector("button").addEventListener("click", () => { addMenu.hidden = true; if (addAt) add(addSheet, addAt.x, addAt.y); });
  document.addEventListener("pointerdown", (e) => { if (!addMenu.contains(e.target)) addMenu.hidden = true; });
  addEventListener("scroll", () => (addMenu.hidden = true), { passive: true });

  window.KASHF_TB = {
    // كلك يمين على مكان فارغ في الورقة (بدون تحديد نص)
    onContext(e) {
      e.preventDefault();
      untilt();
      addSheet = (e.target.closest && e.target.closest(".paper")) || visibleSheet();
      addAt = toPaper(addSheet, e.clientX, e.clientY);
      addMenu.hidden = false;
      addMenu.style.left = Math.min(e.clientX, innerWidth - addMenu.offsetWidth - 8) + "px";
      addMenu.style.top = Math.min(e.clientY, innerHeight - addMenu.offsetHeight - 8) + "px";
      return true;
    },
    getStyle(el) { const b = byId(el.dataset.id) || {}; return { size: b.size || DEF_SIZE, color: b.color || "" }; },
    setStyle(el, patch) {
      const b = byId(el.dataset.id); if (!b) return;
      if ("size" in patch) b.size = patch.size || DEF_SIZE;
      if ("color" in patch) b.color = patch.color || "";
      render(b); saveNow();
    },
    add: addVisible,
    flush: saveNow,
  };

  boxes.forEach((b) => { fit(b); render(b); });
})();
