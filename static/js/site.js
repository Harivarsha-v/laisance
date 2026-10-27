(() => {
  "use strict";
  document.documentElement.classList.remove("no-js");

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const csrf = () => (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "";
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  async function post(url, data) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), "X-Requested-With": "fetch" },
      body: JSON.stringify(data),
    });
    return res.json();
  }

  /* ---- toast + bag count ---- */
  function toast(message, link) {
    let host = $(".flash");
    if (!host) { host = document.createElement("div"); host.className = "flash"; document.body.append(host); }
    const el = document.createElement("div");
    el.className = "toast";
    el.innerHTML = esc(message) + (link ? `<a href="${link.href}">${esc(link.label)}</a>` : "");
    host.append(el);
    setTimeout(() => el.remove(), 4400);
  }
  function setCount(n) {
    $$("[data-bag-count]").forEach((el) => {
      el.textContent = n;
      el.hidden = !n;
      el.classList.remove("bump"); void el.offsetWidth; el.classList.add("bump");
    });
  }

  /* ---- header ---- */
  // solid header once the announcement bar has scrolled away (observer is more reliable than scroll events)
  const header = $(".header"), announce = $(".announce");
  if (header && announce && "IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => header.classList.toggle("is-scrolled", !e.isIntersecting)).observe(announce);
  }
  const menuBtn = $(".menu-btn");
  menuBtn && menuBtn.addEventListener("click", () => {
    const open = $(".nav").classList.toggle("is-open");
    menuBtn.setAttribute("aria-expanded", open);
    menuBtn.textContent = open ? "Close" : "Menu";
  });

  /* ---- headline word reveal ---- */
  $$(".split-words").forEach((el) => {
    let i = 0;
    const walk = (node) => {
      [...node.childNodes].forEach((child) => {
        if (child.nodeType === 3) {
          const frag = document.createDocumentFragment();
          child.textContent.split(/(\s+)/).forEach((part) => {
            if (!part) return;
            if (/^\s+$/.test(part)) { frag.append(part); return; }
            const w = document.createElement("span"); w.className = "w";
            const inner = document.createElement("span"); inner.textContent = part;
            inner.style.animationDelay = `${0.08 * i++ + 0.15}s`;
            w.append(inner); frag.append(w);
          });
          child.replaceWith(frag);
        } else if (child.nodeType === 1 && child.tagName !== "BR") walk(child);
      });
    };
    walk(el);
  });

  /* ---- reveal on scroll ---- */
  const io = "IntersectionObserver" in window && new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
  }, { rootMargin: "0px 0px -6% 0px", threshold: 0 }); // threshold 0 so tall product grids still trigger
  $$(".reveal, .reveal-stagger").forEach((el) => (io ? io.observe(el) : el.classList.add("is-in")));

  /* ---- AI search overlay ---- */
  const panel = $(".search-panel");
  if (panel) {
    const input = $("input", panel), out = $(".suggest", panel), chips = $(".understood", panel);
    const open = () => { panel.classList.add("is-open"); document.body.style.overflow = "hidden"; setTimeout(() => input.focus(), 60); };
    const close = () => { panel.classList.remove("is-open"); document.body.style.overflow = ""; };
    $$("[data-search-open]").forEach((b) => b.addEventListener("click", (e) => { e.preventDefault(); open(); }));
    $$("[data-search-close]", panel).forEach((b) => b.addEventListener("click", close));
    addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
      if (e.key === "/" && !/input|textarea/i.test(document.activeElement.tagName)) { e.preventDefault(); open(); }
    });
    $$("[data-fill]", panel).forEach((b) => b.addEventListener("click", () => { input.value = b.dataset.fill; input.dispatchEvent(new Event("input")); input.focus(); }));
    let timer, seq = 0;
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(async () => {
        const q = input.value.trim(), mine = ++seq;
        if (q.length < 2) { out.innerHTML = ""; chips.innerHTML = ""; return; }
        const data = await fetch(`/api/search/?q=${encodeURIComponent(q)}`).then((r) => r.json());
        if (mine !== seq) return;
        chips.innerHTML = data.understood.length
          ? `<span class="eyebrow">Understood</span>` + data.understood.map((c, i) => `<span class="pill" style="animation-delay:${i * 50}ms">${esc(c)}</span>`).join("")
          : "";
        out.innerHTML = data.results.length
          ? data.results.map((p) => `<a class="card" href="${p.url}">${p.art}<div class="card-meta"><span class="card-name">${esc(p.name)}</span><span class="card-price">${esc(p.price)}</span></div></a>`).join("")
          : `<p class="lede">Nothing yet. Try describing an occasion, a colour or a fabric.</p>`;
      }, 180);
    });
  }

  /* ---- add to bag without reloading ---- */
  $$("form[data-ajax-cart]").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = $("button[type=submit]", form);
      btn && (btn.disabled = true);
      try {
        const res = await fetch(form.action, { method: "POST", body: new FormData(form), headers: { "X-Requested-With": "fetch" } });
        const data = await res.json();
        if (data.error) toast(data.code ? `${data.error} (${data.code})` : data.error);
        else { setCount(data.count); toast(data.message, { href: "/bag/", label: "View bag" }); }
      } finally { btn && (btn.disabled = false); }
    });
  });

  /* ---- newsletter (front-end only) ---- */
  $$("[data-newsletter]").forEach((f) => f.addEventListener("submit", (e) => {
    e.preventDefault();
    f.outerHTML = `<p class="lede" style="margin:22px 0 0">Thank you. You're on the list.</p>`;
  }));

  /* ---- picking a colour relabels it and recolours the gallery artwork ---- */
  $$("[data-color-label]").forEach((label) => {
    $$("input[name=color]").forEach((r) => r.addEventListener("change", () => {
      label.textContent = r.value;
      $$(".gallery .art--drawn").forEach((fig) => {
        fig.style.setProperty("--swatch", r.dataset.hex);
        fig.style.setProperty("--ink", r.dataset.ink);
        $("svg", fig).setAttribute("stroke", r.dataset.ink);
        $$("figcaption", fig).forEach((c) => (c.style.color = r.dataset.ink));
      });
    }));
  });

  /* ---- AI size advisor ---- */
  const advisor = $(".advisor");
  if (advisor) {
    $("[data-advisor-toggle]").addEventListener("click", () => advisor.classList.toggle("is-open"));
    $("form", advisor).addEventListener("submit", async (e) => {
      e.preventDefault();
      const f = new FormData(e.target), result = $(".result", advisor);
      const data = await post("/api/size/", { product: advisor.dataset.product, height: f.get("height"), weight: f.get("weight"), fit: f.get("fit") });
      if (data.error) { result.textContent = data.error; return; }
      result.innerHTML = `We'd suggest <strong>${esc(data.size)}</strong>. ${esc(data.note)} <span class="muted">(${Math.round(data.confidence * 100)}% confident)</span>`;
      $$(".sizes span").forEach((s) => s.classList.remove("is-ai"));
      const radio = $(`.sizes input[value="${CSS.escape(data.size)}"]`);
      if (radio) { radio.checked = true; radio.nextElementSibling.classList.add("is-ai"); }
    });
  }

  /* ---- AI stylist chat ---- */
  const chat = $(".chat");
  if (chat) {
    const log = $(".chat-log", chat), form = $(".chat-form", chat), input = $("input", form), sugg = $(".chat-suggest", chat);
    const scroll = () => (log.scrollTop = log.scrollHeight);

    const renderLook = (look) => {
      if (!look) return "";
      const items = look.items.map((p) => `
        <a class="card" href="${p.url}">${p.art}
          <div class="card-meta"><span class="card-name">${esc(p.name)}</span><span class="card-price muted">${esc(p.price)}${p.color ? " · " + esc(p.color) : ""}</span></div>
        </a>`).join("");
      const add = look.total ? `<button class="btn" data-add-look='${esc(JSON.stringify(look.items.map((i) => ({ id: i.id, color: i.color }))))}'><span>Add the look to your bag</span></button>` : "";
      const total = `<span class="eyebrow">${esc(look.title)}${look.total_display ? " · " + esc(look.total_display) : ""}</span>`;
      return `<div class="look-card"><div class="look-strip">${items}</div><div class="look-foot">${total}${add}</div></div>`;
    };
    const addMsg = (who, html) => {
      const el = document.createElement("div");
      el.className = `msg ${who}`;
      el.innerHTML = html;
      log.append(el); scroll();
      return el;
    };
    const setSuggestions = (list) => {
      sugg.innerHTML = (list || []).map((s) => `<button class="chip" type="button">${esc(s)}</button>`).join("");
    };
    const send = async (text) => {
      text = text.trim();
      if (!text) return;
      addMsg("me", esc(text));
      input.value = "";
      const typing = addMsg("ai", `<div class="typing"><i></i><i></i><i></i></div>`);
      const started = Date.now();
      const res = await fetch("/api/stylist/", {
        method: "POST", body: JSON.stringify({ message: text }),
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), "X-Requested-With": "fetch" },
      });
      const data = await res.json();
      await new Promise((r) => setTimeout(r, Math.max(0, 650 - (Date.now() - started)))); // let the dots breathe
      typing.remove();
      if (data.error) { addMsg("ai", `<div class="txt">${esc(data.error)}</div>`); return; }
      const understood = data.understood.length ? `<div class="understood">${data.understood.map((c) => `<span class="pill">${esc(c)}</span>`).join("")}</div>` : "";
      // stylist text is built server-side from escaped product names, so it is safe to render
      addMsg("ai", `<div class="txt">${data.text}</div>${understood}${renderLook(data.look)}`);
      setSuggestions(data.suggestions);
    };

    form.addEventListener("submit", (e) => { e.preventDefault(); send(input.value); });
    chat.addEventListener("click", async (e) => {
      const chip = e.target.closest(".chip");
      if (chip) { send(chip.textContent); return; }
      const addBtn = e.target.closest("[data-add-look]");
      if (addBtn) {
        addBtn.disabled = true;
        const data = await post("/bag/add-look/", { items: JSON.parse(addBtn.dataset.addLook) });
        setCount(data.count);
        toast(data.message, { href: "/bag/", label: "View bag" });
        addBtn.querySelector("span").textContent = "Added";
      }
    });
    $("[data-chat-reset]", chat).addEventListener("click", async () => {
      await post("/api/stylist/", { reset: true });
      $$(".msg", log).slice(1).forEach((m) => m.remove());
      setSuggestions(JSON.parse(chat.dataset.starters));
    });
    const preset = new URLSearchParams(location.search).get("q");
    if (preset) send(preset);
  }

  /* ---- client-care assistant (every page) ---- */
  const cc = $("[data-concierge]");
  if (cc) {
    const toggle = $(".concierge-toggle", cc), panel = $(".concierge-panel", cc);
    const log = $(".concierge-log", cc), chips = $(".concierge-chips", cc), form = $(".concierge-form", cc), input = $("input", form);
    const starters = (cc.dataset.starters || "").split("|").filter(Boolean);
    const scroll = () => (log.scrollTop = log.scrollHeight);
    const setChips = (list) => (chips.innerHTML = list.map((c) => `<button class="chip" type="button">${esc(c)}</button>`).join(""));
    const open = () => {
      panel.hidden = false;
      requestAnimationFrame(() => cc.classList.add("is-open"));
      toggle.setAttribute("aria-expanded", "true");
      setTimeout(() => input.focus(), 80);
    };
    const close = () => {
      cc.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
      setTimeout(() => { if (!cc.classList.contains("is-open")) panel.hidden = true; }, 350);
    };
    toggle.addEventListener("click", () => (cc.classList.contains("is-open") ? close() : open()));
    $("[data-concierge-close]", cc).addEventListener("click", close);
    addEventListener("keydown", (e) => e.key === "Escape" && cc.classList.contains("is-open") && close());
    setChips(starters);

    const add = (who, html) => {
      const el = document.createElement("div");
      el.className = `cmsg ${who}`;
      el.innerHTML = html;
      log.append(el); scroll();
      return el;
    };

    const ask = async (text) => {
      text = text.trim();
      if (!text) return;
      add("me", `<p>${esc(text)}</p>`);
      input.value = "";
      const typing = add("ai", `<div class="typing"><i></i><i></i><i></i></div>`);
      let data;
      try {
        const res = await fetch("/api/assistant/", {
          method: "POST", body: JSON.stringify({ message: text, page: location.pathname }),
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf(), "X-Requested-With": "fetch" },
        });
        data = await res.json();
      } catch (_) {
        data = { error: "I couldn't reach client care just now. Please try again in a moment.", code: "503" };
      }
      await new Promise((r) => setTimeout(r, 450));
      typing.remove();
      if (data.error) {
        add("ai", `<p>${esc(data.error)}</p><p class="cmsg-meta">Error ${esc(data.code || "")}. Ask me what it means.</p>`);
        return;
      }
      const el = add("ai", data.html + (data.title ? `<p class="cmsg-meta">From: ${esc(data.title)}</p>` : ""));
      if (data.ticket) {
        const f = document.createElement("form");
        f.className = "cmsg-ticket";
        f.innerHTML = `<input type="email" required placeholder="Your email" aria-label="Your email"><button type="submit">Send</button>`;
        f.addEventListener("submit", async (e) => {
          e.preventDefault();
          const r = await post("/api/assistant/ticket/", { ticket: data.ticket, email: $("input", f).value });
          f.outerHTML = `<p class="cmsg-meta">${esc(r.message || r.error)}</p>`;
        });
        el.append(f);
      }
      if (data.log_id && data.kind !== "greeting" && data.kind !== "thanks") {
        const fb = document.createElement("div");
        fb.className = "cmsg-feedback";
        fb.innerHTML = `<span>Was this helpful?</span><button type="button" data-h="1">Yes</button><button type="button" data-h="0">No</button>`;
        fb.addEventListener("click", async (e) => {
          const b = e.target.closest("button");
          if (!b) return;
          await post("/api/assistant/feedback/", { log_id: data.log_id, helpful: b.dataset.h === "1" });
          fb.innerHTML = `<span>${b.dataset.h === "1" ? "Thank you." : "Thank you. We'll use this to improve."}</span>`;
        });
        el.append(fb);
      }
      scroll();
      setChips(data.suggestions && data.suggestions.length ? data.suggestions : starters.slice(0, 2));
    };

    form.addEventListener("submit", (e) => { e.preventDefault(); ask(input.value); });
    chips.addEventListener("click", (e) => { const c = e.target.closest(".chip"); if (c) ask(c.textContent); });
    // any "Ask the assistant" button on the page (FAQ, error codes, error pages)
    $$("[data-ask]").forEach((b) => b.addEventListener("click", () => { open(); if (b.dataset.ask) ask(b.dataset.ask); }));
    window.askAssistant = (q) => { open(); if (q) ask(q); };
  }
})();
