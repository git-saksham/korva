/* KORVA front-end: cart drawer, wishlist, filters, PDP, toasts, validation. Vanilla JS. */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const csrf = () => ($('meta[name="csrf-token"]') || {}).content || "";
  const wrap = Object.assign(document.createElement("div"), { className: "toast-wrap", ariaLive: "polite" });
  document.body.appendChild(wrap);
  function toast(msg, type = "ok") {
    if (!msg) return;
    const t = Object.assign(document.createElement("div"), { className: `k-toast ${type}`, textContent: msg });
    wrap.appendChild(t);
    setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 320); }, 3200);
  }
  window.korvaToast = toast;
  $$("[data-flash]").forEach(el => toast(el.dataset.flash, el.dataset.cat === "danger" ? "err" : "ok"));
  async function api(url, body, method = "POST") {
    const res = await fetch(url, {
      method, credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), Accept: "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = {};
    try { data = await res.json(); } catch (_) {}
    data._status = res.status;
    return data;
  }
  const nav = $(".k-nav");
  if (nav) {
    const overHero = document.body.classList.contains("hero-page");
    const onScroll = () => nav.classList.toggle("solid", !overHero || window.scrollY > 40);
    onScroll(); addEventListener("scroll", onScroll, { passive: true });
  }
  const drawerEl = $("#cartDrawer");
  const drawer = drawerEl ? bootstrap.Offcanvas.getOrCreateInstance(drawerEl) : null;
  function applyCart(d) {
    if (d.html != null) $$("[data-cart-body]").forEach(b => (b.innerHTML = d.html));
    $$("[data-cart-count]").forEach(c => { c.textContent = d.count; c.dataset.n = d.count; });
    const page = $("#cart-page");
    if (page) refreshCartPage();
  }
  async function refreshCartPage() {
    const html = await (await fetch("/cart", { credentials: "same-origin" })).text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const fresh = $("#cart-page", doc);
    if (fresh) $("#cart-page").innerHTML = fresh.innerHTML;
  }
  async function cartCall(url, body, btn) {
    btn && btn.classList.add("loading");
    const d = await api(url, body);
    btn && btn.classList.remove("loading");
    if (d.count != null) applyCart(d);
    if (d.message) toast(d.message, d.ok ? "ok" : "err");
    return d;
  }
  window.korvaCart = { call: cartCall };
  document.addEventListener("click", async e => {
    const open = e.target.closest("[data-open-cart]");
    if (open && drawer) { e.preventDefault(); const d = await api("/cart/state", null, "GET").catch(() => ({})); if (d.html) applyCart(d); drawer.show(); return; }
    const quick = e.target.closest("[data-quick-add]");
    if (quick) {
      e.preventDefault();
      const d = await cartCall("/cart/add", { product_id: quick.dataset.product, size: quick.dataset.size, quantity: 1 });
      if (d.ok && d.open_drawer && drawer) drawer.show();
      return;
    }
    const upd = e.target.closest("[data-cart-qty]");
    if (upd) {
      const item = upd.closest("[data-item]");
      const input = $("input", item);
      const next = Math.max(0, (parseInt(input.value) || 1) + parseInt(upd.dataset.cartQty));
      cartCall("/cart/update", { item_id: item.dataset.item, quantity: next });
      return;
    }
    const rm = e.target.closest("[data-cart-remove]");
    if (rm) { cartCall("/cart/remove", { item_id: rm.closest("[data-item]").dataset.item }); return; }
    const wish = e.target.closest("[data-wish]");
    if (wish) {
      e.preventDefault();
      const d = await api(`/wishlist/toggle/${wish.dataset.wish}`);
      if (d.login) { toast(d.error, "err"); setTimeout(() => (location.href = "/login?next=" + encodeURIComponent(location.pathname + location.search)), 700); return; }
      if (d.ok) { $$(`[data-wish="${wish.dataset.wish}"]`).forEach(b => b.classList.toggle("on", d.saved)); toast(d.message); }
      return;
    }
    const ft = e.target.closest("[data-toggle-filters]");
    if (ft) $(".filters").classList.toggle("open");
  });
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } }), { threshold: .12 });
    $$(".reveal").forEach(el => io.observe(el));
  } else $$(".reveal").forEach(el => el.classList.add("in"));
  const form = $("#filter-form");
  if (form) {
    const results = $("#results");
    let timer, ctl;
    async function run(push = true) {
      const params = new URLSearchParams(new FormData(form));
      [...params.keys()].forEach(k => { if (!params.get(k)) params.delete(k); });
      if (params.get("sort") === "featured") params.delete("sort");
      const qs = params.toString();
      if (push) history.replaceState(null, "", qs ? `?${qs}` : location.pathname);
      results.classList.add("busy");
      ctl && ctl.abort(); ctl = new AbortController();
      params.set("partial", "1");
      try {
        const res = await fetch(`/shop?${params}`, { signal: ctl.signal, credentials: "same-origin" });
        results.innerHTML = await res.text();
      } catch (e) { if (e.name !== "AbortError") toast("Couldn't load products.", "err"); }
      results.classList.remove("busy");
    }
    const sched = (ms = 0) => { clearTimeout(timer); timer = setTimeout(run, ms); };
    form.addEventListener("change", () => sched());
    form.addEventListener("input", e => { if (e.target.matches('[type="search"],[type="number"]')) sched(320); });
    form.addEventListener("submit", e => { e.preventDefault(); sched(); });
    $$('input[type="radio"][data-clearable]', form).forEach(r => r.addEventListener("click", () => {
      if (r.dataset.was === "1") { r.checked = false; r.dataset.was = ""; sched(); }
      else { $$(`input[name="${r.name}"]`, form).forEach(x => (x.dataset.was = "")); r.dataset.was = r.checked ? "1" : ""; }
    }));
    $$('input[type="radio"][data-clearable]:checked', form).forEach(r => (r.dataset.was = "1"));
    $("#clear-filters")?.addEventListener("click", e => { e.preventDefault(); form.reset(); $$("input:not([type=hidden])", form).forEach(i => { if (i.type === "radio") i.checked = false; else if (i.type !== "checkbox") i.value = ""; }); $("select", form) && ($("select", form).value = "featured"); sched(); });
  }
  const sm = $("#searchModal");
  if (sm) {
    const input = $("input", sm), out = $("#search-out", sm);
    sm.addEventListener("shown.bs.modal", () => input.focus());
    let t;
    input.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(async () => {
        const q = input.value.trim();
        if (q.length < 2) { out.innerHTML = ""; return; }
        const d = await (await fetch("/api/search?q=" + encodeURIComponent(q))).json();
        out.innerHTML = d.results.length ? d.results.map(r => `<a class="sres" href="${r.url}"><img src="${r.img}" alt=""><div class="flex-grow-1"><div class="nm">${r.name.replace(/</g, "&lt;")}</div></div><div>${r.price}</div></a>`).join("") : `<p class="muted pt-3">No matches for “${q.replace(/</g, "&lt;")}”.</p>`;
      }, 220);
    });
  }
  const pdp = $("#pdp");
  if (pdp) {
    const variants = JSON.parse($("#variant-data").textContent);
    let color = pdp.dataset.firstColor, size = null, qty = 1;
    const stage = $("#stage img"), stageWrap = $("#stage"), note = $("#stock-note"), add = $("#add-btn");
    const colorLabel = $("#color-label");
    const maxQty = () => { const v = current(); return v ? Math.min(v.stock, 10) : 10; };
    const current = () => variants.find(v => v.color === color && v.size === size);
    function paint() {
      $$(".color-dot").forEach(d => d.classList.toggle("sel", d.dataset.color === color));
      colorLabel.textContent = color;
      $$("#sizes .chip").forEach(c => {
        const v = variants.find(x => x.color === color && x.size === c.dataset.size);
        const out = !v || v.stock <= 0;
        c.disabled = out; c.classList.toggle("sel", c.dataset.size === size && !out);
      });
      if (size && !(current() && current().stock > 0)) size = null;
      const v = current();
      note.className = "stock-note";
      if (!size) { note.textContent = "Select a size"; }
      else if (v.stock <= 5) { note.textContent = `Only ${v.stock} left in ${size}`; note.classList.add("low"); }
      else note.textContent = "In stock — ships in 24h";
      add.disabled = false;
      qty = Math.min(qty, maxQty()); $("#qty").value = qty;
    }
    $$(".color-dot").forEach(d => d.addEventListener("click", () => {
      color = d.dataset.color; const src = d.dataset.img;
      stage.style.opacity = 0; setTimeout(() => { stage.src = src; stage.style.opacity = 1; }, 140);
      $$(".thumb").forEach(t => t.classList.toggle("on", t.dataset.color === color));
      paint();
    }));
    $$(".thumb").forEach(t => t.addEventListener("click", () => $(`.color-dot[data-color="${t.dataset.color}"]`).click()));
    $$("#sizes .chip").forEach(c => c.addEventListener("click", () => { size = c.dataset.size; paint(); }));
    $("#qty-minus").addEventListener("click", () => { qty = Math.max(1, qty - 1); $("#qty").value = qty; });
    $("#qty-plus").addEventListener("click", () => { qty = Math.min(maxQty(), qty + 1); $("#qty").value = qty; });
    $("#qty").addEventListener("change", e => { qty = Math.max(1, Math.min(maxQty(), parseInt(e.target.value) || 1)); e.target.value = qty; });
    const buy = async btn => {
      if (!size) { note.textContent = "Please select a size"; note.className = "stock-note err"; $("#sizes").animate([{ transform: "translateX(-5px)" }, { transform: "translateX(5px)" }, { transform: "none" }], { duration: 260 }); return; }
      const d = await cartCall("/cart/add", { variant_id: current().id, quantity: qty }, btn);
      if (d.ok && d.open_drawer && drawer) drawer.show();
    };
    add.addEventListener("click", () => buy(add));
    $("#sticky-add")?.addEventListener("click", e => buy(e.currentTarget));
    stageWrap.addEventListener("mousemove", e => {
      if (matchMedia("(hover:none)").matches) return;
      const r = stageWrap.getBoundingClientRect();
      stage.style.transformOrigin = `${((e.clientX - r.left) / r.width) * 100}% ${((e.clientY - r.top) / r.height) * 100}%`;
    });
    stageWrap.addEventListener("click", () => stageWrap.classList.toggle("zoom"));
    stageWrap.addEventListener("mouseleave", () => stageWrap.classList.remove("zoom"));
    const sticky = $("#sticky-buy");
    if (sticky) new IntersectionObserver(([en]) => sticky.classList.toggle("show", !en.isIntersecting), { threshold: 0 }).observe(add);
    paint();
  }
  const methods = $$('input[name="method"]');
  if (methods.length) {
    const sync = () => { const m = methods.find(x => x.checked)?.value; $$(".pay-fields").forEach(f => f.classList.toggle("on", f.dataset.method === m)); };
    methods.forEach(m => m.addEventListener("change", sync)); sync();
    const card = $('input[name="card_number"]');
    card?.addEventListener("input", () => { card.value = card.value.replace(/\D/g, "").slice(0, 16).replace(/(.{4})/g, "$1 ").trim(); });
    const exp = $('input[name="card_expiry"]');
    exp?.addEventListener("input", () => { let v = exp.value.replace(/\D/g, "").slice(0, 4); if (v.length > 2) v = v.slice(0, 2) + " / " + v.slice(2); exp.value = v; });
  }
  $$("form.needs-validation").forEach(f => {
    f.addEventListener("submit", e => {
      let ok = true;
      $$("[required]", f).forEach(i => {
        const hidden = i.closest(".pay-fields:not(.on)");
        const bad = !hidden && (!i.value.trim() || (i.type === "email" && !/^\S+@\S+\.\S+$/.test(i.value)) || (i.minLength > 0 && i.value.length < i.minLength));
        i.classList.toggle("is-invalid", bad); if (bad) ok = false;
      });
      const pw = $('[name$="password"]', f), cf = $('[name$="confirm"]', f);
      if (pw && cf && cf.value !== pw.value) { cf.classList.add("is-invalid"); ok = false; }
      if (!ok) { e.preventDefault(); $(".is-invalid", f)?.focus(); toast("Please fix the highlighted fields.", "err"); return; }
      const b = $('[type="submit"]', f); if (b) setTimeout(() => b.classList.add("loading"), 0);
    });
    f.addEventListener("input", e => e.target.classList.remove("is-invalid"));
  });
  $$("[data-stock-input]").forEach(inp => {
    let t;
    inp.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(async () => {
        const d = await api(`/admin/variants/${inp.dataset.stockInput}/stock`, { stock: inp.value });
        if (d.ok) { inp.closest("tr").classList.toggle("low-row", d.low); toast("Stock updated"); } else toast(d.error || "Failed", "err");
      }, 450);
    });
  });
  $$("[data-order-status]").forEach(sel => sel.addEventListener("change", async () => {
    const d = await api(`/admin/orders/${sel.dataset.orderStatus}/status`, { status: sel.value });
    toast(d.ok ? `Order → ${d.status}` : d.error, d.ok ? "ok" : "err");
  }));
  const pm = $("#productModal");
  if (pm) {
    async function load(url) {
      $(".modal-body", pm).innerHTML = '<p class="muted">Loading…</p>';
      $(".modal-body", pm).innerHTML = await (await fetch(url)).text();
      initProductForm($(".modal-body", pm));
    }
    $$("[data-product-form]").forEach(b => b.addEventListener("click", () => { $("#productModalTitle").textContent = b.dataset.title; load(b.dataset.productForm); bootstrap.Modal.getOrCreateInstance(pm).show(); }));
  }
  const om = $("#orderModal");
  if (om) $$("[data-order-view]").forEach(b => b.addEventListener("click", async () => {
    $(".modal-body", om).innerHTML = await (await fetch(b.dataset.orderView)).text();
    bootstrap.Modal.getOrCreateInstance(om).show();
  }));
  function initProductForm(root) {
    const sizes = () => $$('input[name="sizes"]:checked', root).map(i => i.value);
    const colours = () => $$(".color-row", root).map(r => ({ n: $('[name="color_name"]', r).value.trim(), h: $('[name="color_hex"]', r).value })).filter(c => c.n);
    const stockData = JSON.parse(($("#stock-data", root) || { textContent: "{}" }).textContent);
    const body = $("#matrix-body", root);
    function matrix() {
      const keep = {}; $$("input[data-key]", body).forEach(i => (keep[i.dataset.key] = i.value));
      const cs = colours(), ss = sizes();
      body.innerHTML = !cs.length || !ss.length ? '<tr><td class="muted">Pick sizes and add a colour to set stock.</td></tr>' :
        `<tr><th></th>${ss.map(s => `<th>${s}</th>`).join("")}</tr>` + cs.map(c => `<tr><th>${c.n.replace(/</g, "&lt;")}</th>${ss.map(s => { const k = `${s}__${c.n}`; const v = keep[k] ?? stockData[k] ?? 10; return `<td><input class="k-input" type="number" min="0" data-key="${k}" name="stock__${k.replace(/"/g, "&quot;")}" value="${v}"></td>`; }).join("")}</tr>`).join("");
    }
    root.addEventListener("input", e => { if (e.target.matches('[name="color_name"],[name="color_hex"],[name="sizes"]')) matrix(); });
    root.addEventListener("change", e => { if (e.target.matches('[name="sizes"]')) matrix(); });
    root.addEventListener("click", e => {
      if (e.target.closest("#add-color")) { $("#colors", root).insertAdjacentHTML("beforeend", $("#color-tpl", root).innerHTML); }
      const rm = e.target.closest(".rm-color"); if (rm) { rm.closest(".color-row").remove(); matrix(); }
    });
    matrix();
  }
  window.initProductForm = initProductForm;
})();
