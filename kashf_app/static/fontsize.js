/* تنسيق النص على ورقة الاستمارة: حدّد نصاً ← كلك يمين ← حجم الخط واللون.
   يُحفظ في المتصفح لكل استمارة على حدة (ومع الورقة في المحفوظات)، ويظهر في الطباعة. */
(function () {
  "use strict";
  const paper = document.getElementById("paper");
  if (!paper) return;
  const STORE = "kashf-fontsizes:" + location.pathname;
  const MIN = 6, MAX = 48;
  const PRESETS = [9, 10, 11, 12, 13, 14, 16, 18, 20, 24];
  const COLORS = [
    ["#000000", "أسود"], ["#4b5563", "رمادي"], ["#b91c1c", "أحمر"], ["#7f1d1d", "عنابي"], ["#c2410c", "برتقالي"],
    ["#a16207", "ذهبي"], ["#15803d", "أخضر"], ["#1d4ed8", "أزرق"], ["#1e3a8a", "كحلي"], ["#7e22ce", "بنفسجي"],
  ];

  // rules: {t:"k", key, size?, color?}          حقل بيانات كامل (data-k)
  //        {t:"w", path, s, e, size?, color?}   نص ثابت ملفوف بـ span
  let rules = [];
  try { rules = JSON.parse(localStorage.getItem(STORE) || "[]"); } catch (e) { rules = []; }
  if (!Array.isArray(rules)) rules = [];
  const save = () => { try { localStorage.setItem(STORE, JSON.stringify(rules)); } catch (e) {} };
  const isEmptyRule = (r) => !r.size && !r.color;
  function merge(rule, patch) {
    for (const k in patch) { if (patch[k]) rule[k] = patch[k]; else delete rule[k]; }
    return rule;
  }

  /* ---------- مسار ثابت للعناصر (يتجاهل spans التنسيق ومربعات النص) ---------- */
  const isFs = (n) => n.nodeType === 1 && n.classList.contains("fs-w");
  const isSkip = (n) => n.nodeType === 1 && (isFs(n) || n.classList.contains("tb"));
  const staticKids = (el) => [...el.children].filter((c) => !isSkip(c));
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
  // نصوص العنصر بدون محتوى حقول البيانات (لأنها تتغيّر) وبدون مربعات النص
  function staticTexts(el) {
    const out = [];
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (n.parentElement.closest("[data-k],.tb") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
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
      if (pre.comparePoint(t, 0) > 0) break;
      const s = t === pre.startContainer ? pre.startOffset : 0;
      const e = t === pre.endContainer ? pre.endOffset : t.length;
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
  function styleEl(el, rule) {
    el.style.fontSize = rule.size ? rule.size + "px" : "";
    el.style.lineHeight = rule.size ? "1.25" : "";
    // !important حتى لا تلغيه قواعد الطباعة في الصفحة (التي تعيد لون الحقول للأسود)
    if (rule.color) el.style.setProperty("color", rule.color, "important");
    else el.style.removeProperty("color");
  }
  function applyKey(rule) {
    paper.querySelectorAll(`[data-k="${CSS.escape(rule.key)}"]`).forEach((el) => styleEl(el, rule));
  }
  function wrap(range, rule, idx) {
    const span = document.createElement("span");
    span.className = "fs-w";
    span.dataset.fsi = idx;
    styleEl(span, rule);
    span.appendChild(range.extractContents());
    range.insertNode(span);
    // التنسيق الأحدث يغلب على أي تنسيق سابق بداخله لنفس الخاصية
    span.querySelectorAll(".fs-w,[data-k]").forEach((inner) => {
      if (rule.size) { inner.style.fontSize = ""; inner.style.lineHeight = ""; }
      if (rule.color) inner.style.color = "";
    });
    paper.normalize();
    return span;
  }
  function applyWrap(rule, idx) {
    const root = elAt(rule.path);
    if (!root) return;
    const r = rangeAt(root, rule.s, rule.e);
    if (r && !r.collapsed) wrap(r, rule, idx);
  }
  const refreshMeta = () => { try { if (typeof meta === "function") meta(); } catch (e) {} };
  function rebuild() {
    paper.querySelectorAll(".fs-w").forEach((sp) => sp.replaceWith(...sp.childNodes));
    paper.querySelectorAll("[data-k]").forEach((el) => styleEl(el, {}));
    paper.normalize();
    rules.forEach((r, i) => (r.t === "k" ? applyKey(r) : applyWrap(r, i)));
    refreshMeta();
  }
  function reapplyKeys() { rules.forEach((r) => r.t === "k" && applyKey(r)); }

  // أسطر الجدول الإضافية تُبنى من جديد عند التعديل، فنعيد تطبيق تنسيق الحقول بعدها
  if (typeof window.buildPaperRows === "function") {
    const orig = window.buildPaperRows;
    window.buildPaperRows = function () { const r = orig.apply(this, arguments); reapplyKeys(); return r; };
  }

  /* ---------- تحويل التحديد إلى قاعدة ---------- */
  const elOf = (n) => (n.nodeType === 1 ? n : n.parentElement);
  function keysIn(range) {
    const keys = new Set();
    const own = elOf(range.commonAncestorContainer).closest("[data-k]");
    if (own && paper.contains(own)) keys.add(own.dataset.k);
    paper.querySelectorAll("[data-k]").forEach((el) => { if (range.intersectsNode(el) && el.textContent.trim()) keys.add(el.dataset.k); });
    return [...keys];
  }
  function hasStaticText(range) {
    return staticTexts(elOf(range.commonAncestorContainer)).some((t) => {
      if (!range.intersectsNode(t)) return false;
      const s = t === range.startContainer ? range.startOffset : 0;
      const e = t === range.endContainer ? range.endOffset : t.length;
      return t.data.slice(s, e).trim().length > 0;
    });
  }
  // أقرب عنصر يحوي التحديد ولا يتجاوز خلية جدول واحدة
  function wrapRoot(range) {
    let el = elOf(range.commonAncestorContainer);
    while (isFs(el)) el = el.parentElement;
    if (["TR", "TBODY", "TABLE", "THEAD"].includes(el.tagName)) return null;
    if (el.closest("tr.x")) return null;                     // أسطر مضافة ديناميكياً
    return paper.contains(el) && el !== paper ? el : null;
  }

  let touched = [];   // القواعد التي تأثرت بآخر عملية (لإعادة التحديد)
  function setStyle(range, patch) {
    const clearing = Object.values(patch).every((v) => !v);
    keysIn(range).forEach((key) => {
      let rule = rules.find((r) => r.t === "k" && r.key === key);
      if (!rule) { if (clearing) return; rule = { t: "k", key }; rules.push(rule); }
      merge(rule, patch);
      touched.push(rule);
    });

    if (!hasStaticText(range)) return;
    const root = wrapRoot(range);
    if (root) {
      const sFs = elOf(range.startContainer).closest(".fs-w");
      const eFs = elOf(range.endContainer).closest(".fs-w");
      if (sFs && sFs === eFs && rules[+sFs.dataset.fsi]) {
        // التحديد داخل نص منسّق سابقاً بالكامل ← عدّل نفس القاعدة
        const rule = rules[+sFs.dataset.fsi];
        merge(rule, patch);
        touched.push(rule);
        return;
      }
      const path = pathOf(root);
      const s = offsetOf(root, range.startContainer, range.startOffset);
      const e = offsetOf(root, range.endContainer, range.endOffset);
      if (s < 0 || e <= s) return;
      if (clearing) {
        rules.forEach((r) => { if (r && r.t === "w" && r.path.join() === path.join() && r.s < e && r.e > s) merge(r, patch); });
      } else {
        const rule = merge({ t: "w", path, s, e }, patch);
        rules.push(rule);
        touched.push(rule);
      }
    } else if (!keysIn(range).length) {
      // تحديد يتجاوز عدة خلايا: طبّق على النص الثابت في كل خلية متقاطعة
      paper.querySelectorAll("td,th").forEach((td) => {
        if (!range.intersectsNode(td) || td.closest("tr.x") || td.querySelector("td")) return;
        const r = document.createRange();
        r.selectNodeContents(td);
        if (range.compareBoundaryPoints(Range.START_TO_START, r) > 0) r.setStart(range.startContainer, range.startOffset);
        if (range.compareBoundaryPoints(Range.END_TO_END, r) < 0) r.setEnd(range.endContainer, range.endOffset);
        if (!r.collapsed && hasStaticText(r)) setStyle(r, patch);
      });
    }
  }
  function commit() {
    rules = rules.filter((r) => r && !isEmptyRule(r));
    save();
    rebuild();
  }
  // نطاق يغطي العناصر التي تأثرت، حتى يبقى النص محدداً لمواصلة التنسيق
  function touchedRange() {
    const els = [];
    touched.forEach((r) => {
      const i = rules.indexOf(r);
      if (i < 0) return;
      if (r.t === "w") els.push(...paper.querySelectorAll(`.fs-w[data-fsi="${i}"]`));
      else els.push(...[...paper.querySelectorAll(`[data-k="${CSS.escape(r.key)}"]`)].filter((e) => e.textContent.trim()));
    });
    if (!els.length) return null;
    els.sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
    const r = document.createRange();
    const last = els[els.length - 1];
    r.setStart(els[0], 0);
    r.setEnd(last, last.childNodes.length);
    return r;
  }
  function resetAll() {
    rules = [];
    save();
    rebuild();
  }

  /* ---------- القائمة ---------- */
  const css = document.createElement("style");
  css.textContent = `
  #paper{-webkit-user-select:text;user-select:text}
  #paper ::selection{background:rgba(212,165,78,.45)}
  .fsm{position:fixed;z-index:9999;width:252px;padding:10px;border-radius:14px;background:#15181e;color:#eceef1;
    border:1px solid rgba(255,255,255,.14);box-shadow:0 18px 50px rgba(0,0,0,.55);font:13px "IBM Plex Sans Arabic",Tahoma,sans-serif;
    direction:rtl;opacity:0;transform:scale(.96) translateY(-4px);transform-origin:top right;transition:opacity .12s,transform .12s;pointer-events:none}
  .fsm.on{opacity:1;transform:none;pointer-events:auto}
  .fsm .h{display:flex;justify-content:space-between;align-items:center;gap:8px;color:#8a919a;font-size:12px;margin:0 2px 8px}
  .fsm .h b{color:#eceef1;font-weight:600;font-size:13px;white-space:nowrap}
  .fsm .h .sel{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .fsm .lbl{color:#8a919a;font-size:11.5px;margin:2px 2px 6px}
  .fsm .row{display:flex;align-items:center;gap:6px;margin-bottom:8px}
  .fsm button{font:inherit;color:inherit;cursor:pointer;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);border-radius:8px;padding:6px 0;transition:background .12s,border-color .12s}
  .fsm button:hover{background:rgba(255,255,255,.09);border-color:rgba(255,255,255,.25)}
  .fsm .step{width:40px;font-size:17px;line-height:1}
  .fsm .val{flex:1;display:flex;align-items:center;justify-content:center;gap:4px;border:1px solid rgba(212,165,78,.4);background:rgba(212,165,78,.1);border-radius:8px;padding:2px 6px}
  .fsm .val input{width:46px;background:none;border:0;outline:0;color:#f1cd85;font:500 15px "IBM Plex Mono",Consolas,monospace;text-align:center}
  .fsm .val span{color:#8a919a;font-size:11px}
  .fsm .grid{display:grid;grid-template-columns:repeat(5,1fr);gap:5px;margin-bottom:10px}
  .fsm .grid button{font:500 12px "IBM Plex Mono",Consolas,monospace}
  .fsm .grid button.on{border-color:#d4a54e;color:#f1cd85;background:rgba(212,165,78,.12)}
  .fsm .sw{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-bottom:10px}
  .fsm .sw button{height:26px;padding:0;border-radius:7px;border:2px solid rgba(255,255,255,.15);position:relative}
  .fsm .sw button.on{border-color:#f1cd85;box-shadow:0 0 0 2px rgba(241,205,133,.25)}
  .fsm .sw button.def{background:repeating-linear-gradient(45deg,#fff 0 4px,#ddd 4px 8px);color:#000;font-size:10px;font-weight:700}
  .fsm .sw label{height:26px;border-radius:7px;border:2px dashed rgba(255,255,255,.25);display:grid;place-items:center;cursor:pointer;font-size:14px;overflow:hidden;position:relative}
  .fsm .sw label input{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;border:0;padding:0}
  .fsm .foot{display:flex;gap:6px;border-top:1px solid rgba(255,255,255,.08);padding-top:8px}
  .fsm .foot button{flex:1;font-size:12px;padding:7px 0}
  .fsm .foot .danger{color:#ff6b5b;border-color:rgba(255,107,91,.3)}
  .fs-tip{position:fixed;z-index:9998;left:50%;bottom:18px;transform:translateX(-50%) translateY(10px);opacity:0;transition:.2s;
    background:#15181e;border:1px solid rgba(212,165,78,.35);color:#eceef1;border-radius:999px;padding:8px 16px;font:12.5px "IBM Plex Sans Arabic",Tahoma,sans-serif;pointer-events:none;direction:rtl;white-space:nowrap}
  .fs-tip.on{opacity:1;transform:translateX(-50%)}
  @media print{.fsm,.fs-tip{display:none!important}}`;
  document.head.appendChild(css);

  const menu = document.createElement("div");
  menu.className = "fsm";
  menu.innerHTML = `
    <div class="h"><b>تنسيق النص</b><span class="sel"></span></div>
    <div class="lbl">حجم الخط</div>
    <div class="row">
      <button type="button" class="step" data-d="-1" title="تصغير">−</button>
      <label class="val"><input type="number" min="${MIN}" max="${MAX}" step="1" aria-label="حجم الخط"><span>px</span></label>
      <button type="button" class="step" data-d="1" title="تكبير">+</button>
    </div>
    <div class="grid">${PRESETS.map((p) => `<button type="button" data-p="${p}">${p}</button>`).join("")}</div>
    <div class="lbl">اللون</div>
    <div class="sw">
      ${COLORS.map(([c, n]) => `<button type="button" data-c="${c}" title="${n}" style="background:${c}"></button>`).join("")}
      <label title="لون آخر">+<input type="color" value="#b91c1c" aria-label="اختيار لون آخر"></label>
      <button type="button" class="def" data-c="" title="اللون الافتراضي">A</button>
    </div>
    <div class="foot">
      <button type="button" data-a="reset">إزالة التنسيق</button>
      <button type="button" data-a="all" class="danger">إزالة كل التنسيق</button>
    </div>`;
  document.body.appendChild(menu);
  const input = menu.querySelector(".val input"), selLbl = menu.querySelector(".sel"), picker = menu.querySelector('input[type="color"]');
  let saved = null, boxTarget = null;

  const tip = document.createElement("div");
  tip.className = "fs-tip";
  document.body.appendChild(tip);
  let tipT;
  function toast(msg) { tip.textContent = msg; tip.classList.add("on"); clearTimeout(tipT); tipT = setTimeout(() => tip.classList.remove("on"), 2200); }

  const TB = () => window.KASHF_TB || null;
  function selRange() {
    const sel = getSelection();
    if (!sel.rangeCount || sel.isCollapsed) return null;
    const r = sel.getRangeAt(0);
    return paper.contains(r.commonAncestorContainer) && r.toString().trim() ? r : null;
  }
  const toHex = (c) => {
    const m = String(c).match(/\d+/g);
    return m && m.length >= 3 ? "#" + m.slice(0, 3).map((n) => (+n).toString(16).padStart(2, "0")).join("") : "";
  };
  function markSize(v) { menu.querySelectorAll("[data-p]").forEach((b) => b.classList.toggle("on", +b.dataset.p === v)); }
  function markColor(hex, isDefault) {
    menu.querySelectorAll("[data-c]").forEach((b) => b.classList.toggle("on", isDefault ? b.dataset.c === "" : b.dataset.c === hex));
  }
  function showCurrent(el, isDefaultColor) {
    const cs = getComputedStyle(el);
    const v = Math.round(parseFloat(cs.fontSize) || 14);
    input.value = v; markSize(v);
    markColor(toHex(cs.color), isDefaultColor);
  }
  function place(x, y) {
    menu.classList.add("on");
    const w = menu.offsetWidth, h = menu.offsetHeight;
    menu.style.left = Math.max(8, Math.min(x - w, innerWidth - w - 8)) + "px";
    menu.style.top = Math.max(8, Math.min(y, innerHeight - h - 8)) + "px";
  }
  function label(txt) {
    txt = txt.trim().replace(/\s+/g, " ");
    selLbl.textContent = txt ? "«" + (txt.length > 18 ? txt.slice(0, 18) + "…" : txt) + "»" : "";
  }
  function open(x, y, range) {
    boxTarget = null;
    saved = range.cloneRange();
    const n = elOf(range.startContainer);
    showCurrent(n, !n.closest(".fs-w,[data-k]") || !(n.closest(".fs-w,[data-k]").style.color));
    label(range.toString());
    place(x, y);
  }
  function openBox(x, y, box) {
    saved = null; boxTarget = box;
    const st = TB().getStyle(box);
    const content = box.querySelector(".tb-t") || box;
    showCurrent(content, !st.color);
    label(content.innerText || "مربع نص");
    place(x, y);
  }
  function close() { menu.classList.remove("on"); }
  function restoreSel() {
    if (!saved) return;
    const sel = getSelection(); sel.removeAllRanges(); sel.addRange(saved);
  }
  function apply(patch) {
    if ("size" in patch) patch.size = patch.size ? Math.max(MIN, Math.min(MAX, Math.round(patch.size))) : 0;
    if (boxTarget) {
      TB().setStyle(boxTarget, patch);
      showCurrent(boxTarget.querySelector(".tb-t") || boxTarget, !TB().getStyle(boxTarget).color);
      return;
    }
    if (!saved) return;
    touched = [];
    setStyle(saved, patch);
    commit();
    const r = touchedRange();
    if (r) { saved = r; restoreSel(); }
    if (patch.size) { input.value = patch.size; markSize(patch.size); }
    if ("color" in patch) markColor(patch.color, !patch.color);
  }

  paper.addEventListener("contextmenu", (e) => {
    const r = selRange();
    const box = e.target.closest && e.target.closest(".tb");
    const tb = TB();
    // تحديد داخل مربع نص، أو كلك يمين على مربع نص ← تنسيق المربع كله
    if (tb && (box || (r && elOf(r.commonAncestorContainer).closest(".tb")))) {
      e.preventDefault();
      openBox(e.clientX, e.clientY, box || elOf(r.commonAncestorContainer).closest(".tb"));
      return;
    }
    if (r) { e.preventDefault(); open(e.clientX, e.clientY, r); return; }
    if (tb && tb.onContext(e)) return;
    toast("حدّد كلمة أو نصاً أولاً، ثم اضغط كلك يمين");
  });
  // الأجهزة اللمسية: افتح القائمة بعد التحديد مباشرة
  if (matchMedia("(pointer:coarse)").matches) {
    let t;
    document.addEventListener("selectionchange", () => {
      clearTimeout(t);
      t = setTimeout(() => {
        const r = selRange();
        if (!r || menu.classList.contains("on") || elOf(r.commonAncestorContainer).closest(".tb")) return;
        const b = r.getBoundingClientRect();
        open(b.right, b.bottom + 10, r);
      }, 700);
    });
  }
  menu.addEventListener("mousedown", (e) => { if (!e.target.closest("input")) e.preventDefault(); });
  menu.addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.dataset.d) apply({ size: (+input.value || 14) + +b.dataset.d });
    else if (b.dataset.p) apply({ size: +b.dataset.p });
    else if ("c" in b.dataset) apply({ color: b.dataset.c });
    else if (b.dataset.a === "reset") {
      apply({ size: 0, color: "" });
      if (!boxTarget) { saved = null; getSelection().removeAllRanges(); }
      close(); toast("أُزيل التنسيق");
    } else if (b.dataset.a === "all") {
      if (confirm("إزالة كل تنسيقات الحجم واللون في هذه الاستمارة؟")) { resetAll(); close(); toast("أُزيل كل التنسيق"); }
    }
  });
  picker.addEventListener("input", () => apply({ color: picker.value }));
  input.addEventListener("change", () => apply({ size: +input.value }));
  input.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); apply({ size: +input.value }); } });
  document.addEventListener("mousedown", (e) => { if (!menu.contains(e.target)) close(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
  addEventListener("scroll", close, { passive: true });
  addEventListener("resize", close);

  rebuild();
})();
