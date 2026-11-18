/* التحكم بحجم الخط في الاستمارة: حدّد نصاً على الورقة ← كلك يمين ← اختر الحجم.
   يُحفظ في المتصفح لكل استمارة على حدة، ويُطبَّق أيضاً عند الطباعة. */
(function () {
  "use strict";
  const paper = document.getElementById("paper");
  if (!paper) return;
  const STORE = "kashf-fontsizes:" + location.pathname;
  const MIN = 6, MAX = 48;
  const PRESETS = [9, 10, 11, 12, 13, 14, 16, 18, 20, 24];

  // rules: {t:"k", key, size}  حقل بيانات كامل (data-k)
  //        {t:"w", path, s, e, size}  نص ثابت ملفوف بـ span
  let rules = [];
  try { rules = JSON.parse(localStorage.getItem(STORE) || "[]"); } catch (e) { rules = []; }
  if (!Array.isArray(rules)) rules = [];
  const save = () => { try { localStorage.setItem(STORE, JSON.stringify(rules)); } catch (e) {} };

  /* ---------- مسار ثابت للعناصر (يتجاهل spans الحجم وأسطر الجدول المضافة) ---------- */
  const isFs = (n) => n.nodeType === 1 && n.classList.contains("fs-w");
  const staticKids = (el) => [...el.children].filter((c) => !isFs(c));
  function pathOf(el) {
    const p = [];
    while (el && el !== paper) {
      if (!isFs(el)) p.unshift(staticKids(el.parentElement).indexOf(el));
      el = el.parentElement;
    }
    return p;
  }
  function elAt(path) {
    let el = paper;
    for (const i of path) { el = el && staticKids(el)[i]; }
    return el || null;
  }
  // نصوص العنصر بدون محتوى حقول البيانات (لأنها تتغيّر)
  function staticTexts(el) {
    const out = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement.closest("[data-k]") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    for (let n; (n = w.nextNode()); ) out.push(n);
    return out;
  }
  // موضع (node, off) كعدد أحرف النص الثابت قبله داخل root
  function offsetOf(root, node, off) {
    if (!root.contains(node) && root !== node) return -1;
    const pre = document.createRange();
    pre.setStart(root, 0);
    pre.setEnd(node, off);
    let total = 0;
    for (const t of staticTexts(root)) {
      if (!pre.intersectsNode(t)) continue;
      const s = t === pre.startContainer ? pre.startOffset : 0;
      const e = t === pre.endContainer ? pre.endOffset : t.length;
      if (pre.comparePoint(t, 0) > 0) break;
      total += Math.max(0, e - s);
    }
    return total;
  }
  function rangeAt(root, s, e) {
    const r = document.createRange();
    let total = 0, started = false;
    for (const t of staticTexts(root)) {
      const len = t.length;
      if (!started && s <= total + len) { r.setStart(t, s - total); started = true; }
      if (started && e <= total + len) { r.setEnd(t, e - total); return r; }
      total += len;
    }
    return null;
  }

  /* ---------- تطبيق القواعد ---------- */
  function applyKey(rule) {
    paper.querySelectorAll(`[data-k="${CSS.escape(rule.key)}"]`).forEach((el) => {
      el.style.fontSize = rule.size ? rule.size + "px" : "";
      if (rule.size) el.style.lineHeight = "1.25";
    });
  }
  function wrap(range, size, idx) {
    const span = document.createElement("span");
    span.className = "fs-w";
    span.dataset.fsi = idx;
    span.style.fontSize = size + "px";
    span.style.lineHeight = "1.25";
    span.appendChild(range.extractContents());
    range.insertNode(span);
    span.querySelectorAll(".fs-w").forEach((inner) => {           // دمج أي تحديد سابق بداخله
      inner.style.fontSize = ""; inner.style.lineHeight = "";
    });
    paper.normalize();
    return span;
  }
  function applyWrap(rule, idx) {
    const root = elAt(rule.path);
    if (!root) return;
    const r = rangeAt(root, rule.s, rule.e);
    if (r && !r.collapsed) wrap(r, rule.size, idx);
  }
  function applyAll() {
    rules.forEach((r, i) => (r.t === "k" ? applyKey(r) : applyWrap(r, i)));
    refreshMeta();
  }
  function reapplyKeys() { rules.forEach((r) => r.t === "k" && applyKey(r)); }
  const refreshMeta = () => { try { if (typeof meta === "function") meta(); } catch (e) {} };

  // أسطر الجدول الإضافية تُبنى من جديد عند التعديل، فنعيد تطبيق أحجام الحقول بعدها
  if (typeof window.buildPaperRows === "function") {
    const orig = window.buildPaperRows;
    window.buildPaperRows = function () { const r = orig.apply(this, arguments); reapplyKeys(); return r; };
  }

  /* ---------- تحويل التحديد إلى قاعدة ---------- */
  function keysIn(range) {
    const keys = new Set();
    const anc = range.commonAncestorContainer;
    const own = (anc.nodeType === 1 ? anc : anc.parentElement).closest("[data-k]");
    if (own && paper.contains(own)) keys.add(own.dataset.k);
    paper.querySelectorAll("[data-k]").forEach((el) => { if (range.intersectsNode(el) && el.textContent.trim()) keys.add(el.dataset.k); });
    return [...keys];
  }
  function hasStaticText(range) {
    const anc = range.commonAncestorContainer;
    const root = anc.nodeType === 1 ? anc : anc.parentElement;
    return staticTexts(root).some((t) => {
      if (!range.intersectsNode(t)) return false;
      const s = t === range.startContainer ? range.startOffset : 0;
      const e = t === range.endContainer ? range.endOffset : t.length;
      return t.data.slice(s, e).trim().length > 0;
    });
  }
  // أقرب عنصر يحوي التحديد ولا يتجاوز خلية جدول واحدة
  function wrapRoot(range) {
    let el = range.commonAncestorContainer;
    if (el.nodeType !== 1) el = el.parentElement;
    while (isFs(el)) el = el.parentElement;
    if (["TR", "TBODY", "TABLE", "THEAD"].includes(el.tagName)) return null;
    if (el.closest("tr.x")) return null;                     // أسطر مضافة ديناميكياً
    return paper.contains(el) && el !== paper ? el : null;
  }

  let touched = [];   // القواعد التي تأثرت بآخر عملية (لإعادة التحديد)
  function setSize(range, size) {
    const keys = keysIn(range);
    keys.forEach((key) => {
      rules = rules.filter((r) => !(r.t === "k" && r.key === key));
      const rule = { t: "k", key, size };
      if (size) rules.push(rule);
      touched.push(rule);
      applyKey(rule);
    });

    if (hasStaticText(range)) {
      const root = wrapRoot(range);
      if (root) {
        // تحديد داخل span حجم موجود بالكامل ← عدّل نفس القاعدة
        const sNode = range.startContainer, eNode = range.endContainer;
        const sFs = (sNode.nodeType === 1 ? sNode : sNode.parentElement).closest(".fs-w");
        const eFs = (eNode.nodeType === 1 ? eNode : eNode.parentElement).closest(".fs-w");
        if (sFs && sFs === eFs && rules[+sFs.dataset.fsi]) {
          const idx = +sFs.dataset.fsi;
          if (size) {
            rules[idx].size = size;
            touched.push(rules[idx]);
            paper.querySelectorAll(`.fs-w[data-fsi="${idx}"]`).forEach((el) => (el.style.fontSize = size + "px"));
          } else {
            rules[idx] = null;
            unwrapAll(idx);
          }
        } else {
          const path = pathOf(root);
          const s = offsetOf(root, range.startContainer, range.startOffset);
          const e = offsetOf(root, range.endContainer, range.endOffset);
          if (s >= 0 && e > s) {
            if (size) {
              const rule = { t: "w", path, s, e, size };
              rules.push(rule);
              touched.push(rule);
              wrap(range, size, rules.length - 1);
            } else {
              // إعادة الافتراضي: احذف القواعد المتداخلة في نفس العنصر
              rules.forEach((r, i) => {
                if (r && r.t === "w" && r.path.join() === path.join() && r.s < e && r.e > s) { rules[i] = null; unwrapAll(i); }
              });
            }
          }
        }
      } else if (!keys.length) {
        // تحديد يتجاوز عدة خلايا: طبّق على النص الثابت في كل خلية متقاطعة
        paper.querySelectorAll("td,th").forEach((td) => {
          if (!range.intersectsNode(td) || td.closest("tr.x") || td.querySelector("td")) return;
          const r = document.createRange();
          r.selectNodeContents(td);
          if (range.compareBoundaryPoints(Range.START_TO_START, r) > 0) r.setStart(range.startContainer, range.startOffset);
          if (range.compareBoundaryPoints(Range.END_TO_END, r) < 0) r.setEnd(range.endContainer, range.endOffset);
          if (!r.collapsed && hasStaticText(r)) setSize(r, size);
        });
      }
    }
  }
  function commit() {
    rules = rules.filter(Boolean);
    save();
    rebuildIndices();
    refreshMeta();
  }
  // نطاق يغطي العناصر التي تأثرت، حتى يبقى النص محدداً لمواصلة التكبير/التصغير
  function touchedRange() {
    const els = [];
    touched.forEach((r) => {
      const i = rules.indexOf(r);
      if (r.t === "w" && i >= 0) els.push(...paper.querySelectorAll(`.fs-w[data-fsi="${i}"]`));
      if (r.t === "k") els.push(...[...paper.querySelectorAll(`[data-k="${CSS.escape(r.key)}"]`)].filter((e) => e.textContent.trim()));
    });
    if (!els.length) return null;
    els.sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
    const r = document.createRange();
    const last = els[els.length - 1];
    r.setStart(els[0], 0);
    r.setEnd(last, last.childNodes.length);
    return r;
  }
  function unwrapAll(idx) {
    paper.querySelectorAll(`.fs-w[data-fsi="${idx}"]`).forEach((sp) => {
      sp.replaceWith(...sp.childNodes);
    });
    paper.normalize();
  }
  // بعد حذف قواعد تتغيّر الفهارس: أعد ترقيم spans
  function rebuildIndices() {
    // الطريقة الأبسط والأضمن: أعد البناء من القواعد المحفوظة
    paper.querySelectorAll(".fs-w").forEach((sp) => sp.replaceWith(...sp.childNodes));
    paper.normalize();
    rules.forEach((r, i) => r.t === "w" && applyWrap(r, i));
  }
  function resetAll() {
    rules = [];
    save();
    paper.querySelectorAll(".fs-w").forEach((sp) => sp.replaceWith(...sp.childNodes));
    paper.querySelectorAll("[data-k]").forEach((el) => { el.style.fontSize = ""; el.style.lineHeight = ""; });
    paper.normalize();
    refreshMeta();
  }

  /* ---------- القائمة ---------- */
  const css = document.createElement("style");
  css.textContent = `
  #paper{-webkit-user-select:text;user-select:text}
  #paper ::selection{background:rgba(212,165,78,.45)}
  .fsm{position:fixed;z-index:9999;min-width:232px;padding:10px;border-radius:14px;background:#15181e;color:#eceef1;
    border:1px solid rgba(255,255,255,.14);box-shadow:0 18px 50px rgba(0,0,0,.55);font:13px "IBM Plex Sans Arabic",Tahoma,sans-serif;
    direction:rtl;opacity:0;transform:scale(.96) translateY(-4px);transform-origin:top right;transition:opacity .12s,transform .12s;pointer-events:none}
  .fsm.on{opacity:1;transform:none;pointer-events:auto}
  .fsm .h{display:flex;justify-content:space-between;align-items:center;color:#8a919a;font-size:12px;margin:0 2px 8px}
  .fsm .h b{color:#eceef1;font-weight:600;font-size:13px}
  .fsm .row{display:flex;align-items:center;gap:6px;margin-bottom:8px}
  .fsm button{font:inherit;color:inherit;cursor:pointer;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);border-radius:8px;padding:6px 0;transition:background .12s,border-color .12s}
  .fsm button:hover{background:rgba(255,255,255,.09);border-color:rgba(255,255,255,.25)}
  .fsm .step{width:40px;font-size:17px;line-height:1}
  .fsm .val{flex:1;display:flex;align-items:center;justify-content:center;gap:4px;border:1px solid rgba(212,165,78,.4);background:rgba(212,165,78,.1);border-radius:8px;padding:2px 6px}
  .fsm .val input{width:46px;background:none;border:0;outline:0;color:#f1cd85;font:500 15px "IBM Plex Mono",Consolas,monospace;text-align:center}
  .fsm .val span{color:#8a919a;font-size:11px}
  .fsm .grid{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-bottom:8px}
  .fsm .grid button{font:500 12px "IBM Plex Mono",Consolas,monospace}
  .fsm .grid button.on{border-color:#d4a54e;color:#f1cd85;background:rgba(212,165,78,.12)}
  .fsm .foot{display:flex;gap:6px;border-top:1px solid rgba(255,255,255,.08);padding-top:8px}
  .fsm .foot button{flex:1;font-size:12px;padding:7px 0}
  .fsm .foot .danger{color:#ff6b5b;border-color:rgba(255,107,91,.3)}
  .fsm .hint{color:#8a919a;font-size:11.5px;margin:2px 2px 0;line-height:1.5}
  .fs-tip{position:fixed;z-index:9998;left:50%;bottom:18px;transform:translateX(-50%) translateY(10px);opacity:0;transition:.2s;
    background:#15181e;border:1px solid rgba(212,165,78,.35);color:#eceef1;border-radius:999px;padding:8px 16px;font:12.5px "IBM Plex Sans Arabic",Tahoma,sans-serif;pointer-events:none;direction:rtl}
  .fs-tip.on{opacity:1;transform:translateX(-50%)}
  @media print{.fsm,.fs-tip{display:none!important}}`;
  document.head.appendChild(css);

  const menu = document.createElement("div");
  menu.className = "fsm";
  menu.innerHTML = `
    <div class="h"><b>حجم الخط</b><span class="sel"></span></div>
    <div class="row">
      <button type="button" class="step" data-d="-1" title="تصغير">−</button>
      <label class="val"><input type="number" min="${MIN}" max="${MAX}" step="1"><span>px</span></label>
      <button type="button" class="step" data-d="1" title="تكبير">+</button>
    </div>
    <div class="grid">${PRESETS.map((p) => `<button type="button" data-p="${p}">${p}</button>`).join("")}</div>
    <div class="foot">
      <button type="button" data-a="reset">الحجم الافتراضي</button>
      <button type="button" data-a="all" class="danger">إعادة كل الأحجام</button>
    </div>`;
  document.body.appendChild(menu);
  const input = menu.querySelector("input"), selLbl = menu.querySelector(".sel");
  let saved = null;

  const tip = document.createElement("div");
  tip.className = "fs-tip";
  document.body.appendChild(tip);
  let tipT;
  function toast(msg) { tip.textContent = msg; tip.classList.add("on"); clearTimeout(tipT); tipT = setTimeout(() => tip.classList.remove("on"), 2200); }

  function selRange() {
    const sel = getSelection();
    if (!sel.rangeCount || sel.isCollapsed) return null;
    const r = sel.getRangeAt(0);
    return paper.contains(r.commonAncestorContainer) && r.toString().trim() ? r : null;
  }
  function currentSize(range) {
    let n = range.startContainer;
    if (n.nodeType !== 1) n = n.parentElement;
    return Math.round(parseFloat(getComputedStyle(n).fontSize) || 14);
  }
  function markPreset(v) { menu.querySelectorAll("[data-p]").forEach((b) => b.classList.toggle("on", +b.dataset.p === v)); }
  function open(x, y, range) {
    saved = range.cloneRange();
    const v = currentSize(range);
    input.value = v; markPreset(v);
    const txt = range.toString().trim().replace(/\s+/g, " ");
    selLbl.textContent = "«" + (txt.length > 18 ? txt.slice(0, 18) + "…" : txt) + "»";
    menu.classList.add("on");
    const w = menu.offsetWidth, h = menu.offsetHeight;
    menu.style.left = Math.max(8, Math.min(x - w, innerWidth - w - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(y, innerHeight - h - 8)) + "px";
  }
  function close() { menu.classList.remove("on"); }
  function restoreSel() {
    if (!saved) return;
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(saved);
  }
  function apply(size) {
    if (!saved) return;
    size = size ? Math.max(MIN, Math.min(MAX, Math.round(size))) : 0;
    touched = [];
    setSize(saved, size);
    commit();
    if (!size) { saved = null; getSelection().removeAllRanges(); close(); toast("أُعيد الحجم الافتراضي"); return; }
    input.value = size; markPreset(size);
    const r = touchedRange();
    if (r) { saved = r; restoreSel(); }
  }

  paper.addEventListener("contextmenu", (e) => {
    const r = selRange();
    if (!r) { toast("حدّد كلمة أو نصاً أولاً، ثم اضغط كلك يمين"); return; }
    e.preventDefault();
    open(e.clientX, e.clientY, r);
  });
  // الأجهزة اللمسية: افتح القائمة بعد التحديد مباشرة
  if (matchMedia("(pointer:coarse)").matches) {
    let t;
    document.addEventListener("selectionchange", () => {
      clearTimeout(t);
      t = setTimeout(() => {
        const r = selRange();
        if (!r || menu.classList.contains("on")) return;
        const b = r.getBoundingClientRect();
        open(b.right, b.bottom + 10, r);
      }, 700);
    });
  }
  menu.addEventListener("mousedown", (e) => { if (e.target !== input) e.preventDefault(); });
  menu.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.d) apply((+input.value || 14) + +b.dataset.d);
    else if (b.dataset.p) apply(+b.dataset.p);
    else if (b.dataset.a === "reset") apply(0);
    else if (b.dataset.a === "all") { if (confirm("إعادة كل أحجام الخط في هذه الاستمارة إلى الافتراضي؟")) { resetAll(); close(); toast("أُعيدت كل الأحجام"); } }
  });
  input.addEventListener("change", () => apply(+input.value));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); apply(+input.value); } });
  document.addEventListener("mousedown", (e) => { if (!menu.contains(e.target)) close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  addEventListener("scroll", close, { passive: true });
  addEventListener("resize", close);

  applyAll();
})();
