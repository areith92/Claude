"use strict";
(function () {
  const D = window.DASHBOARD;
  const SVGNS = "http://www.w3.org/2000/svg";
  const state = { filter: "all" };
  const reduced = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  const motion = { on: (function () {
    let v = null;
    try { v = localStorage.getItem("motion"); } catch (e) { v = null; }
    return v === "on" ? true : v === "off" ? false : !reduced;
  })(), chosen: (function () { try { return localStorage.getItem("motion") !== null; } catch (e) { return false; } })() };
  function motionButton() {
    const b = h("button", { class: "btn", type: "button" }), note = h("span", { class: "empty" });
    const paint = function () {
      b.textContent = "Motion: " + (motion.on ? "on" : "off");
      note.textContent = reduced && !motion.chosen ? " Off because your system asks for reduced motion. Click to turn it on." : "";
    };
    b.addEventListener("click", function () {
      motion.on = !motion.on; motion.chosen = true;
      try { localStorage.setItem("motion", motion.on ? "on" : "off"); } catch (e) { /* storage unavailable */ }
      paint();
    });
    paint();
    return h("span", null, b, note);
  }

  function add(e, kids) {
    kids.flat(3).forEach(function (k) {
      if (k != null && k !== false) e.append(k.nodeType ? k : document.createTextNode(String(k)));
    });
    return e;
  }
  function h(tag, attrs) {
    const e = document.createElement(tag);
    Object.entries(attrs || {}).forEach(function (kv) {
      if (kv[0] === "class") e.className = kv[1];
      else if (kv[0].indexOf("on") === 0) e.addEventListener(kv[0].slice(2), kv[1]);
      else if (kv[1] != null && kv[1] !== false) e.setAttribute(kv[0], kv[1]);
    });
    return add(e, [].slice.call(arguments, 2));
  }
  function sv(tag, attrs) {
    const e = document.createElementNS(SVGNS, tag);
    Object.entries(attrs || {}).forEach(function (kv) {
      if (kv[0].indexOf("on") === 0) e.addEventListener(kv[0].slice(2), kv[1]);
      else if (kv[1] != null && kv[1] !== false) e.setAttribute(kv[0], kv[1]);
    });
    return add(e, [].slice.call(arguments, 2));
  }

  const gbp = function (n) { return "£" + Number(n || 0).toFixed(2); };
  const deptById = function (id) {
    return (D.departments || []).find(function (d) { return d.id === id; }) ||
      { id: id, label: id, color: "#8899aa", agents: [], tools: [] };
  };
  const agentByName = function (n) { return (D.agents || []).find(function (a) { return a.name === n; }); };
  const agentColor = function (a) { return a.dept === "conductor" ? "#5ad1ff" : deptById(a.dept).color; };
  const plural = function (n, w) { return n + " " + w + (n === 1 ? "" : "s"); };
  const pill = function (t, c) { return h("span", { class: "pill " + (c || "") }, t); };
  const chip = function (t, c) { return h("span", { class: "chip " + (c || "") }, t); };
  const tierLabel = { auto: "auto tier", needs_approval: "owner approval", needs_owner_and_accountant: "owner + accountant" };
  const tierCls = { auto: "ok", needs_approval: "warn", needs_owner_and_accountant: "bad" };

  function copyBtn(text, label) {
    const base = label || "Copy command";
    const b = h("button", { class: "copy", type: "button", title: text }, base);
    b.addEventListener("click", function () {
      const say = function (m) { b.textContent = m; setTimeout(function () { b.textContent = base; }, 1400); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(function () { say("Copied"); }, function () { say("Copy failed"); });
      else say("Copy failed");
    });
    return b;
  }
  function stat(label, value, sub, cls) {
    return h("div", { class: "stat " + (cls || "") }, h("span", { class: "k" }, label), h("b", null, value),
      sub ? h("span", { class: "sub" }, sub) : null);
  }
  function head(kicker, title, right) {
    return h("header", { class: "phead" },
      h("div", null, h("div", { class: "kicker" }, "// " + kicker), h("h1", null, title, h("span", { class: "cursor" }))), right || null);
  }
  function panel(title) {
    return add(h("section", { class: "panel" }, title ? h("div", { class: "ptitle" }, title) : null), [].slice.call(arguments, 1));
  }
  function table(cols, rows, onRow, emptyText) {
    if (!rows.length) return h("div", { class: "empty" }, emptyText || "Nothing yet.");
    const tb = h("tbody", null);
    rows.forEach(function (r) {
      const tr = h("tr", onRow ? { class: "click" } : null, r.cells.map(function (c) { return h("td", null, c); }));
      if (onRow) tr.addEventListener("click", function () { onRow(r.data); });
      tb.append(tr);
    });
    return h("div", { class: "wrap" }, h("table", null, h("thead", null, h("tr", null, cols.map(function (c) { return h("th", null, c); }))), tb));
  }
  function bar(spent, cap) {
    const p = cap > 0 ? Math.min(spent / cap * 100, 100) : 0;
    const cls = p >= 100 ? "bad" : p >= 80 ? "warn" : "";
    const i = h("i", null);
    i.style.width = p + "%";
    return h("div", { class: "bar " + cls }, i);
  }

  /* ---------- drawer ---------- */
  function closeDrawer() { document.getElementById("drawer-root").replaceChildren(); }
  function section(title, body) { return h("div", { class: "dsec" }, h("div", { class: "ptitle" }, title), body); }
  function drawer(kicker, title, kids) {
    const root = document.getElementById("drawer-root");
    root.replaceChildren(
      h("div", { class: "shade", onclick: closeDrawer }),
      add(h("aside", { class: "drawer", role: "dialog", "aria-label": title },
        h("div", { class: "dtop" }, h("span", null, kicker), h("button", { class: "btn", type: "button", onclick: closeDrawer }, "Close")),
        h("h3", null, title)), kids));
  }
  function ladder() {
    const rows = [["HUMAN-LED", "You do it by hand. No agent involved.", false],
      ["HUMAN-ASSISTED", "The agent drafts. You approve and carry it out. This is how every task works today.", true],
      ["FULLY AUTONOMOUS", "The agent acts alone. Not available: live actions are off until Phase 3.", false]];
    return h("div", { class: "ladder" }, rows.map(function (r) { return h("div", { class: r[2] ? "on" : "" }, h("b", null, r[0]), h("span", null, r[1])); }));
  }
  function humanText(t) {
    if (t.status === "replied") return "Read the reply, then record your decision with the decide command (see Tasks).";
    if (t.status === "delegated") return "Paste the prepared prompt into the AI it names, then save the reply in inbox/ with the same file name.";
    if (t.status === "approved") return "Carry it out by hand, then mark it complete.";
    if (t.status === "blocked") return t.note || "Blocked. Check the note.";
    return "No action needed.";
  }
  function taskDrawer(t) {
    const a = agentByName(t.agent);
    const tier = t.tier_effective || t.tier;
    const needs = { auto: "No approval needed for the draft.", needs_approval: "The owner must approve before anything is done.",
      needs_owner_and_accountant: "Needs the owner and the accountant to approve." }[tier];
    drawer(t.id, t.objective, [
      h("div", { class: "badges" }, pill(tierLabel[tier] || tier, tierCls[tier]), pill("draft only", "mut"), pill(t.status)),
      t.why ? h("p", null, t.why) : null,
      section("BUILDS ON", h("div", { class: "chips" }, chip(t.agent + " agent"), a ? chip(a.model) : null)),
      section("WHAT IT NEEDS", h("p", null, needs || "")),
      t.flags && t.flags.length ? section("FLAGS", h("div", { class: "chips" }, t.flags.map(function (f) { return chip(f, "bad"); }))) : null,
      t.reply_file || t.prompt_file ? section("FILE", h("p", { class: "mono" }, t.reply_file || t.prompt_file)) : null,
      section("THE LADDER", ladder()),
      section("THE HUMAN", h("p", null, humanText(t)))]);
  }
  function sopSection(a) {
    const s = a.sop;
    if (!s || !s.exists) {
      return section("STANDING PROCEDURE (SOP)", h("p", { class: "empty" }, "No SOP found at " + (s ? s.path : "memory/brain/sops/" + a.name + ".md") + "."));
    }
    return section("STANDING PROCEDURE (SOP)", h("div", null, h("p", null, s.purpose),
      h("ol", { class: "sop" }, s.steps.map(function (x) { return h("li", null, x); })),
      h("p", { class: "empty" }, "Approval: " + s.tier),
      s.escalate.length ? h("p", { class: "empty" }, "Escalate to the owner: " + s.escalate.join("; ")) : null,
      h("p", { class: "mono" }, s.path)));
  }
  function agentDrawer(a) {
    const tasks = D.tasks.filter(function (t) { return t.agent === a.name; });
    const d = a.dept === "conductor" ? { label: "Conductor", color: "#5ad1ff" } : deptById(a.dept);
    drawer(d.label.toUpperCase(), a.name, [
      h("div", { class: "badges" }, pill(a.enabled ? "enabled" : "disabled", a.enabled ? "ok" : "mut"), pill(a.mode + " mode"), pill(a.dry_run ? "draft only" : "live", a.dry_run ? "mut" : "bad")),
      h("p", null, a.role || "No role text found in agents/" + a.name + "/prompt.md."),
      section("MODEL", h("div", { class: "chips" }, chip(a.model), chip(a.provider))),
      section("AI SPEND THIS MONTH", h("div", null, h("div", null, gbp(a.spent_gbp) + " of " + gbp(a.cap_gbp) + " cap"), bar(a.spent_gbp, a.cap_gbp))),
      section("TASKS", tasks.length ? h("div", { class: "chips" }, tasks.map(function (t) { return chip(t.id + " · " + t.status); })) : h("p", { class: "empty" }, "No tasks queued.")),
      sopSection(a),
      section("LIMITS", h("p", null, "Proposes only. Cannot change governance, permissions or workflows. No customer personal data."))]);
  }
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeDrawer(); });

  /* ---------- shared blocks ---------- */
  function banner() {
    const s = D.spend;
    const label = { ok: "AI spend is within budget", warning: "AI spend warning: nearing the monthly cap",
      stopped: "AI spend STOPPED: monthly cap reached", off: "Paid AI use is switched off" }[s.state] || s.state;
    return [h("div", { class: "banner " + s.state }, h("b", null, label), h("span", null, gbp(s.spent_gbp) + " of £" + s.cap_gbp + " · " + D.month)),
      D.mode.paused ? h("div", { class: "banner stopped" }, h("b", null, "ALL AGENTS PAUSED (kill switch)")) : null];
  }
  function decisions() {
    const items = D.approvals.map(function (a) {
      return h("div", { class: "decision" },
        h("div", { class: "top" }, h("b", null, a.id), pill(tierLabel[a.tier] || a.tier, tierCls[a.tier]), chip(a.agent), a.flags.map(function (f) { return chip(f, "bad"); })),
        h("div", null, a.objective), a.reply_file ? h("div", { class: "mono" }, a.reply_file) : null,
        copyBtn(a.approve, "Copy approve"), copyBtn(a.reject, "Copy reject"), copyBtn(a.defer, "Copy defer"));
    });
    return panel("NEEDS YOUR DECISION", items.length ? items : [h("div", { class: "empty" }, "Nothing waiting."),
      copyBtn('python3 scripts/orchestrate.py plan --goal "Draft the first three listings"', "Copy: plan some work")]);
  }
  function callsTable() {
    return table(["Date", "Agent", "Model", "Tokens", "Cost"], D.recent_costs.map(function (r) {
      return { cells: [r.date, r.agent, r.model, r.tokens, gbp(r.cost_gbp)] };
    }), null, "No AI calls logged yet.");
  }

  /* ---------- pages ---------- */
  function home() {
    const s = D.spend;
    const on = D.agents.filter(function (a) { return a.enabled; }).length;
    const live = D.agents.filter(function (a) { return a.enabled && a.mode === "api"; }).length;
    const q = Object.entries(D.queue).map(function (kv) { return kv[0] + " " + kv[1]; }).join(" · ");
    return [head("overview", "COMMERCE OS"), banner(), supportBanner(),
      h("div", { class: "grid stats" },
        stat("AI SPEND · MTD", gbp(s.spent_gbp), "of £" + s.cap_gbp + " cap", s.state === "stopped" ? "bad" : s.state === "warning" ? "warn" : ""),
        stat("NEEDS YOUR DECISION", String(D.approvals.length), D.approvals.length ? "see Tasks" : "all clear", D.approvals.length ? "warn" : ""),
        stat("TASKS", String(D.tasks.length), q || "none yet"),
        stat("AGENTS", on + "/" + D.agents.length, live + " on the API"),
        stat("MODE", D.mode.provider || "manual", D.mode.dry_run_default ? "draft only · no live actions" : "live actions on"),
        stat("TECH SUPPORT", String(openInc().length), fixReady().length ? plural(fixReady().length, "fix") + " ready" : "open incidents", fixReady().length ? "warn" : openInc().length ? "bad" : "")),
      h("div", { class: "cols" }, decisions(),
        panel("DEPARTMENTS", h("div", { class: "deptchips" }, D.departments.map(function (d) {
          return h("a", { class: "deptchip", href: "#core/" + d.id, style: "--c:" + d.color }, h("i"), h("div", null, d.label, h("small", null, plural(d.agents.length, "agent"))));
        })))),
      panel("RECENT AI CALLS", callsTable()),
      D.latest_digest ? panel("LATEST DIGEST", h("p", { class: "mono" }, "reports/digests/" + D.latest_digest)) : null];
  }
  function tasksPage() {
    return [head("work queue", "TASKS"), decisions(),
      panel("ALL TASKS", table(["ID", "Agent", "Task", "Tier", "Status"], D.tasks.map(function (t) {
        const tier = t.tier_effective || t.tier;
        return { data: t, cells: [t.id, t.agent, t.objective, pill(tierLabel[tier] || tier, tierCls[tier]), pill(t.status)] };
      }), taskDrawer, "No tasks yet. Use the plan command on the Home page."))];
  }
  function agentsPage() {
    return [head("workforce", "AGENTS"), h("div", { class: "agentgrid" }, D.agents.map(function (a) {
      return h("button", { class: "acard", type: "button", style: "--c:" + agentColor(a), onclick: function () { agentDrawer(a); } },
        h("b", null, h("span", { class: a.enabled ? "dot" : "dot off" }), a.name), h("p", null, a.role),
        h("div", { class: "chips" }, chip(a.model), chip(a.mode), a.enabled ? null : chip("disabled"), a.sop && a.sop.exists ? chip("SOP") : chip("no SOP", "bad")),
        bar(a.spent_gbp, a.cap_gbp), h("small", null, gbp(a.spent_gbp) + " of " + gbp(a.cap_gbp)));
    }))];
  }
  function orgPage() {
    const c = agentByName(D.conductor);
    const card = function (a) {
      return h("button", { class: "mini", type: "button", onclick: function () { agentDrawer(a); } },
        h("span", { class: a.enabled ? "dot" : "dot off" }), a.name, h("small", null, a.model + " · " + a.mode));
    };
    return [head("agent hierarchy", "ORG CHART"), h("div", { class: "org" },
      h("div", { class: "node" }, h("b", null, "You"), h("span", { class: "empty" }, "OWNER · approves everything")),
      h("div", { class: "vline" }),
      h("div", { class: "orgrow" }, h("div", { class: "sidecard" }, "KNOWLEDGE CORE", h("br"), D.brain.count + " notes in memory/brain"),
        h("div", { class: "node conductor", onclick: function () { if (c) agentDrawer(c); } }, h("span", { class: "kicker" }, "CONDUCTOR · SUPER AGENT"),
          h("b", null, D.conductor), c ? h("div", { class: "chips" }, chip(c.model), chip(c.mode + " mode")) : null,
          h("span", { class: "empty" }, "plan · delegate · review · digest")),
        h("div", { class: "sidecard" }, "DIGEST FEED", h("br"), D.latest_digest || "no digest yet")),
      h("div", { class: "vline" }),
      h("div", { class: "deptrow" }, D.departments.map(function (d) {
        return h("div", { class: "dcol", style: "--c:" + d.color }, h("div", { class: "dhead" }, d.label, h("span", null, plural(d.agents.length, "agent"))),
          d.agents.map(agentByName).filter(Boolean).map(card), h("div", { class: "chips" }, d.tools.map(function (t) { return chip(t); })));
      })))];
  }

  /* ---------- knowledge core ---------- */
  function seeded(seed) { let x = seed; return function () { x = (x * 16807) % 2147483647; return x / 2147483647; }; }
  function brainCloud(cx, cy, r, count, seed) {
    const g = sv("g", { class: "cloud" }), rnd = seeded(seed), R = r - 6, LINK = 22, MAXL = 340, SPEED = 2.5, pts = [], lines = [];
    for (let i = 0; i < count; i++) {
      const a = rnd() * Math.PI * 2, d = Math.sqrt(rnd()) * R, s = (8 + rnd() * 12) * SPEED, t = rnd() * Math.PI * 2;
      pts.push({ x: cx + Math.cos(a) * d, y: cy + Math.sin(a) * d, vx: Math.cos(t) * s, vy: Math.sin(t) * s });
    }
    for (let i = 0; i < MAXL; i++) { const l = sv("line", { class: "cl", visibility: "hidden" }); lines.push(l); g.append(l); }
    pts.forEach(function (p, i) {
      p.el = sv("circle", { cx: p.x, cy: p.y, r: i % 9 === 0 ? 2.6 : 1.5, class: "cp", style: "animation-delay:" + ((i % 12) * 0.25) + "s" });
      g.append(p.el);
    });
    g.append(sv("circle", { cx: cx, cy: cy, r: r, class: "brain" }));
    function frame(dt) {
      pts.forEach(function (p) {
        p.vx += (Math.random() - 0.5) * 70 * SPEED * dt;
        p.vy += (Math.random() - 0.5) * 70 * SPEED * dt;
        const sp = Math.hypot(p.vx, p.vy) || 1, k = Math.min(Math.max(sp, 8 * SPEED), 22 * SPEED) / sp;
        p.vx *= k; p.vy *= k;
        p.x += p.vx * dt; p.y += p.vy * dt;
        const dx = p.x - cx, dy = p.y - cy, dist = Math.hypot(dx, dy);
        if (dist > R) {
          const nx = dx / dist, ny = dy / dist, dot = p.vx * nx + p.vy * ny;
          p.x = cx + nx * R; p.y = cy + ny * R;
          if (dot > 0) { p.vx -= 2 * dot * nx; p.vy -= 2 * dot * ny; }
        }
        p.el.setAttribute("cx", p.x.toFixed(1));
        p.el.setAttribute("cy", p.y.toFixed(1));
      });
      let k = 0;
      for (let i = 0; i < pts.length && k < MAXL; i++) {
        for (let j = i + 1; j < pts.length && k < MAXL; j++) {
          if ((i + j) % 3 !== 0) continue;
          const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y, d2 = dx * dx + dy * dy;
          if (d2 >= LINK * LINK) continue;
          const l = lines[k++];
          l.setAttribute("x1", pts[i].x.toFixed(1)); l.setAttribute("y1", pts[i].y.toFixed(1));
          l.setAttribute("x2", pts[j].x.toFixed(1)); l.setAttribute("y2", pts[j].y.toFixed(1));
          l.style.strokeOpacity = (0.18 + 0.35 * (1 - Math.sqrt(d2) / LINK)).toFixed(2);
          l.setAttribute("visibility", "visible");
        }
      }
      for (; k < MAXL; k++) lines[k].setAttribute("visibility", "hidden");
    }
    frame(0);
    let last = 0;
    const tick = function (ts) {
      if (!g.isConnected) return;
      if (motion.on && ts - last >= 16) { frame(Math.min((ts - last) / 1000, 0.1)); last = ts; }
      else if (!motion.on) last = ts;
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    return g;
  }
  function people(x, y) {
    return sv("g", { class: "ic", transform: "translate(" + x + "," + y + ")" },
      sv("circle", { cx: -5, cy: -4, r: 3.5 }), sv("circle", { cx: 5, cy: -4, r: 3.5 }),
      sv("path", { d: "M-11 8 Q-5 0 0 6 Q5 0 11 8" }));
  }
  function radial(filter) {
    const cx = 430, cy = 430, n = D.departments.length;
    const svg = sv("svg", { viewBox: "40 40 780 780", class: "graph", role: "img", "aria-label": "Map of departments, agents and tools" });
    [150, 250, 370].forEach(function (r) { svg.append(sv("circle", { cx: cx, cy: cy, r: r, class: "ring" })); });
    svg.append(brainCloud(cx, cy, 84, 150, 7));
    const pos = function (r, a) { return [cx + Math.cos(a) * r, cy + Math.sin(a) * r]; };
    D.departments.forEach(function (d, i) {
      const ang = -Math.PI / 2 + i * 2 * Math.PI / n, dp = pos(150, ang);
      const g = sv("g", { class: "dept" + (filter !== "all" && filter !== d.id ? " dim" : ""), style: "--c:" + d.color });
      g.append(sv("line", { x1: cx, y1: cy, x2: dp[0], y2: dp[1], class: "spoke" }));
      d.agents.forEach(function (name, k) {
        const a = agentByName(name), aa = ang + (k - (d.agents.length - 1) / 2) * 0.2, ap = pos(250, aa), lp = pos(276, aa);
        g.append(sv("line", { x1: dp[0], y1: dp[1], x2: ap[0], y2: ap[1], class: "link" }));
        g.append(sv("g", { class: "agent" + (a && a.enabled ? "" : " off"), onclick: function (e) { e.stopPropagation(); if (a) agentDrawer(a); } },
          sv("circle", { cx: ap[0], cy: ap[1], r: 14 }), sv("text", { x: ap[0], y: ap[1] + 4, "text-anchor": "middle", class: "ico" }, "A"), sv("title", null, name)));
        g.append(sv("text", { x: lp[0], y: lp[1] + 3, "text-anchor": Math.cos(aa) >= 0 ? "start" : "end", class: "lbl" }, name));
      });
      d.tools.forEach(function (name, k) {
        const tp = pos(370, ang + (k - (d.tools.length - 1) / 2) * 0.16);
        g.append(sv("circle", { cx: tp[0], cy: tp[1], r: 7, class: "tool" }, sv("title", null, name)));
      });
      const dn = sv("g", { class: "dn", onclick: function () { location.hash = "#core/" + d.id; } },
        sv("circle", { cx: dp[0], cy: dp[1], r: 24 }), people(dp[0], dp[1]), sv("title", null, "Open " + d.label));
      g.append(dn, sv("text", { x: dp[0], y: dp[1] + 42, class: "dlabel" }, d.label));
      svg.append(g);
    });
    return svg;
  }
  function drill(d) {
    const W = 900, H = 640, ags = d.agents.map(agentByName).filter(Boolean), m = ags.length;
    const svg = sv("svg", { viewBox: "0 0 " + W + " " + H, class: "graph", style: "--c:" + d.color, role: "img", "aria-label": d.label + " department" });
    svg.append(sv("text", { x: W / 2, y: 36, "text-anchor": "middle", class: "gtitle", fill: d.color }, d.label.toUpperCase()));
    const xs = ags.map(function (_, i) { return m === 1 ? W / 2 : 140 + i * (W - 280) / (m - 1); });
    const tx = d.tools.map(function (_, i) { return d.tools.length === 1 ? W / 2 : 150 + i * (W - 300) / (d.tools.length - 1); });
    const dept = [W / 2, 575];
    xs.forEach(function (x) { tx.forEach(function (t) { svg.append(sv("line", { x1: x, y1: 200, x2: t, y2: 100, class: "faint" })); }); });
    d.tools.forEach(function (name, i) {
      svg.append(sv("circle", { cx: tx[i], cy: 100, r: 9, class: "tool" }), sv("text", { x: tx[i], y: 82, class: "gsmall" }, name));
    });
    let any = false;
    ags.forEach(function (a, i) {
      svg.append(sv("g", { class: "agent" + (a.enabled ? "" : " off"), style: "--c:" + d.color, onclick: function () { agentDrawer(a); } },
        sv("circle", { cx: xs[i], cy: 200, r: 20 }), sv("text", { x: xs[i], y: 205, "text-anchor": "middle", class: "ico" }, "A")));
      svg.append(sv("text", { x: xs[i], y: 242, class: "gsmall" }, a.name), sv("text", { x: xs[i], y: 256, class: "gsmall" }, a.model));
      D.tasks.filter(function (t) { return t.agent === a.name; }).slice(0, 3).forEach(function (t, j) {
        any = true;
        const y = 310 + j * 52, label = t.objective.length > 28 ? t.objective.slice(0, 27) + "…" : t.objective;
        svg.append(sv("line", { x1: xs[i], y1: j ? y - 52 + 8 : 220, x2: xs[i], y2: y - 8, stroke: "#cfe3ff", "stroke-opacity": ".5" }),
          sv("line", { x1: xs[i], y1: y + 8, x2: dept[0], y2: dept[1] - 28, class: "gdash" }),
          sv("g", { class: "agent tnode", onclick: function () { taskDrawer(t); } }, sv("rect", { x: xs[i] - 7, y: y - 7, width: 14, height: 14, rx: 3, fill: "#0a1222", stroke: d.color }),
            sv("title", null, t.objective)),
          sv("text", { x: xs[i], y: y + 24, class: "gsmall" }, label));
      });
    });
    if (!any) svg.append(sv("text", { x: W / 2, y: 380, class: "gsmall" }, "No tasks queued for this department yet."));
    svg.append(sv("g", { class: "dept" }, sv("g", { class: "dn" }, sv("circle", { cx: dept[0], cy: dept[1], r: 28 }), people(dept[0], dept[1]))),
      sv("text", { x: dept[0], y: dept[1] + 48, class: "dlabel", fill: d.color }, d.label));
    return svg;
  }
  function corePage(arg) {
    const d = arg && D.departments.find(function (x) { return x.id === arg; });
    const f = state.filter;
    const sel = h("select", { "aria-label": "Department filter", onchange: function (e) { state.filter = e.target.value; render(); } },
      h("option", { value: "all" }, "Department · all"),
      D.departments.map(function (x) { return h("option", { value: x.id, selected: f === x.id ? "selected" : null }, x.label); }));
    const tools = D.departments.reduce(function (n, x) { return n + x.tools.length; }, 0);
    const legend = [["#ff6b81", "Brain notes", D.brain.count], ["#5ad1ff", "Departments", D.departments.length], ["#cfe3ff", "AI agents", D.agents.length],
      ["#ff4d6d", "Tools", tools], ["#fbbf24", "Tasks", D.tasks.length]];
    return [head("knowledge core", d ? d.label.toUpperCase() : "COMMERCE ENGINE",
        h("div", { class: "infobox" }, D.brain.count + " notes in memory/brain (" + D.agents.filter(function (a) { return a.sop && a.sop.exists; }).length + " SOPs) · markdown · add notes by pull request")),
      h("div", { class: "tabs" }, h("span", { class: "tab on" }, "Radial"), d ? h("a", { class: "btn", href: "#core" }, "← Back") : null, motionButton()),
      h("div", { class: "cols graphcols" }, h("div", { class: "graphbox" }, d ? drill(d) : radial(f)),
        h("div", null, panel("FILTER", sel),
          panel("LEGEND", h("div", { class: "legend" }, legend.map(function (l) {
            return h("div", { style: "--c:" + l[0] }, h("i", { class: "sw" }), l[1], h("span", null, String(l[2])));
          }))),
          panel("DIRECTORY", h("div", { class: "dir" }, D.agents.map(function (a) {
            return h("button", { type: "button", style: "--c:" + agentColor(a), onclick: function () { agentDrawer(a); } },
              h("i", { class: "sw" }), a.name, h("small", null, a.dept === "conductor" ? "conductor" : deptById(a.dept).label));
          })))))];
  }

  /* ---------- finances, health, connections, roadmap ---------- */
  function donut(items, total) {
    const colors = ["#5ad1ff", "#ff4d6d", "#34d399", "#fbbf24", "#a78bfa", "#22d3ee", "#fb923c", "#e879f9"];
    const r = 70, C = 2 * Math.PI * r;
    let off = 0;
    const svg = sv("svg", { viewBox: "0 0 200 200", class: "donut", role: "img", "aria-label": "AI spend by agent" }, sv("circle", { cx: 100, cy: 100, r: r, class: "dbg" }));
    items.forEach(function (it, i) {
      const len = total > 0 ? C * it.spent_gbp / total : 0;
      svg.append(sv("circle", { cx: 100, cy: 100, r: r, class: "dseg", stroke: colors[i % colors.length], "stroke-dasharray": len + " " + (C - len), "stroke-dashoffset": -off, transform: "rotate(-90 100 100)" }));
      off += len;
    });
    svg.append(sv("text", { x: 100, y: 102, "text-anchor": "middle", class: "dnum" }, gbp(total)), sv("text", { x: 100, y: 120, "text-anchor": "middle", class: "dsub" }, "this month"));
    return [svg, colors];
  }
  function financesPage() {
    const s = D.spend, items = D.per_agent.filter(function (a) { return a.spent_gbp > 0; });
    const dn = donut(items, s.spent_gbp), ebay = D.connections.find(function (c) { return c.id === "ebay"; });
    const colorFor = function (name) { const i = items.findIndex(function (x) { return x.agent === name; }); return i < 0 ? "#44546f" : dn[1][i % dn[1].length]; };
    return [head("every cost, one view", "FINANCES"), banner(),
      h("div", { class: "grid stats" },
        stat("AI SPEND · MTD", gbp(s.spent_gbp), s.percent + "% of cap", s.state === "stopped" ? "bad" : s.state === "warning" ? "warn" : ""),
        stat("CAP REMAINING", gbp(s.remaining_gbp), "of £" + s.cap_gbp),
        stat("INCOME · MTD", "—", "awaiting eBay API (Phase 2)"), stat("NET", "—", "needs income data")),
      panel("AI SPEND BY AGENT · " + D.month, h("div", { class: "donutwrap" }, dn[0],
        h("div", { style: "flex:1;min-width:260px" }, D.per_agent.length ? D.per_agent.map(function (a, i) {
          return h("div", { class: "brow" }, h("span", null, h("i", { class: "sw", style: "--c:" + colorFor(a.agent) + ";margin-right:8px;display:inline-block;vertical-align:-2px" }), a.agent), bar(a.spent_gbp, a.cap_gbp), h("span", null, gbp(a.spent_gbp) + " / " + gbp(a.cap_gbp)));
        }) : h("div", { class: "empty" }, "No agent has a spend cap above zero."))),
        h("p", { class: "empty" }, "Costs are estimates from token counts and the prices in models/costs.yml. Gemini is on the free tier and is not counted.")),
      panel("INCOME · BY CHANNEL", h("div", { class: "cards" }, [
        h("div", { class: "decision" }, h("b", null, "eBay UK"), h("div", { class: "empty" }, ebay ? ebay.status : "manual mode"), pill("not connected", "mut")),
        h("div", { class: "decision" }, h("b", null, "Shopify"), h("div", { class: "empty" }, "Reserved for Phase 4"), pill("not enabled", "mut"))]))];
  }
  function healthPage() {
    const s = D.spend, allDry = D.agents.every(function (a) { return a.dry_run; });
    const checks = [
      [D.mode.paused ? "bad" : "ok", "Kill switch", D.mode.paused ? "PAUSED: no agent will run" : "Running. Use the Kill switch workflow to stop everything."],
      [s.state === "ok" ? "ok" : s.state === "off" ? "warn" : "bad", "Budget guard", "State: " + s.state + ". Calls that could pass a cap are never sent."],
      [allDry ? "ok" : "warn", "Draft only", allDry ? "Every agent is in dry-run mode." : "Some agents are not in dry-run mode."],
      ["ok", "Personal-data guard", "run_agent.py refuses prompts that look like they contain personal data."],
      [D.approvals.length ? "warn" : "ok", "Decisions waiting", D.approvals.length + " task(s) need your decision."],
      [D.latest_digest ? "ok" : "warn", "Owner digest", D.latest_digest || "No digest yet. Run the digest command."],
      [openInc().length ? "bad" : "ok", "Tech Support", openInc().length + " open incident(s). Run python3 scripts/techsupport.py detect to check."],
      [D.agents.every(function (a) { return a.sop && a.sop.exists; }) ? "ok" : "warn", "SOPs", D.agents.filter(function (a) { return a.sop && a.sop.exists; }).length + " of " + D.agents.length + " agents have a SOP in memory/brain/sops/."]];
    return [head("system checks", "HEALTH"), panel(null, checks.map(function (c) {
      return h("div", { class: "check" }, h("span", { class: c[0] === "ok" ? "dot" : "dot off", style: c[0] === "ok" ? null : "background:" + (c[0] === "bad" ? "#ff4d6d" : "#fbbf24") }),
        h("div", null, h("b", null, c[1]), h("small", null, c[2])));
    }))];
  }
  function connectionsPage() {
    return [head("plumbing", "CONNECTIONS"), h("div", { class: "cards" }, D.connections.map(function (c) {
      return h("div", { class: "panel" }, h("div", { class: "ptitle" }, c.name.toUpperCase()), pill(c.status, /in use|enabled/.test(c.status) ? "ok" : "mut"), h("p", null, c.detail));
    }))];
  }
  function roadmapPage() {
    return [head("autonomy ladder", "ROADMAP"), D.phases.list.map(function (p) {
      return h("div", { class: "phase" + (p.n === D.phases.current ? " now" : "") }, h("div", { class: "n" }, String(p.n)),
        h("div", null, h("b", null, p.name), " ", pill(p.n === D.phases.current ? "now" : "later", p.n === D.phases.current ? "ok" : "mut"), h("p", { class: "empty" }, p.text)));
    })];
  }

  /* ---------- tech support ---------- */
  const STAGES = ["Detected", "Raised", "Diagnosed", "Fix tested", "Implemented", "Verified", "Shipped"];
  const incList = function () { return D.incidents || []; };
  const openInc = function () { return incList().filter(function (i) { return i.status !== "resolved" && i.status !== "abandoned"; }); };
  const fixReady = function () { return incList().filter(function (i) { return i.status === "ready_to_ship"; }); };
  const incCls = { ready_to_ship: "ok", resolved: "ok", fix_failed: "bad", needs_owner: "warn", raised: "bad", abandoned: "mut" };
  function stageBar(done) {
    return h("div", { class: "stages" }, STAGES.map(function (s, i) {
      return h("div", { class: "stage" + (i < done ? " done" : i === done ? " now" : "") }, h("i"), h("span", null, s));
    }));
  }
  function supportBanner() {
    const ready = fixReady(), open = openInc();
    if (ready.length) {
      return h("div", { class: "banner" }, h("b", null, "FIX READY: " + ready.map(function (i) { return i.id; }).join(", ")),
        h("span", null, "Verified in your working tree. Open Tech Support to ship it."), h("a", { class: "btn", href: "#support" }, "Open"));
    }
    if (open.length) {
      return h("div", { class: "banner stopped" }, h("b", null, plural(open.length, "open incident")),
        h("span", null, "Tech Support can work on it."), h("a", { class: "btn", href: "#support" }, "Open"));
    }
    return null;
  }
  function incidentDrawer(i) {
    drawer(i.id, i.title, [
      h("div", { class: "badges" }, pill(i.severity, i.severity === "high" ? "bad" : "warn"), pill(i.status.replace(/_/g, " "), incCls[i.status]), chip("check: " + i.check)),
      stageBar(i.stage),
      section("EVIDENCE", h("pre", { class: "evidence" }, i.evidence || "none")),
      i.diagnosis ? section("DIAGNOSIS", h("p", null, i.diagnosis + (i.root_cause ? " Root cause: " + i.root_cause : ""))) : null,
      i.fix ? section("PROPOSED CHANGES", h("div", { class: "chips" }, i.fix.files.map(function (f) {
        return chip(f.path + " · " + f.op + " · " + (f.kind === "apply" ? "Tech Support may apply" : "owner-only"), f.kind === "apply" ? "" : "bad");
      }))) : null,
      i.test ? section("SCRATCH TEST", h("p", null, (i.test.passed ? "PASSED. " : "FAILED. ") + i.test.summary)) : null,
      i.live ? section("WORKING-TREE CHECK", h("p", null, (i.live.passed ? "PASSED. " : "FAILED. ") + i.live.summary)) : null,
      i.branch ? section("BRANCH", h("p", { class: "mono" }, i.branch)) : null,
      section("WHAT HAPPENED", h("div", null, i.history.map(function (x) { return h("div", { class: "empty" }, x.date + " · " + x.status + " · " + x.note); }))),
      section("NEXT STEPS", i.next.length ? h("div", null, i.next.map(function (n) {
        return h("div", null, h("div", { class: "empty" }, n.label), copyBtn(n.cmd, "Copy command"), h("div", { class: "mono" }, n.cmd));
      })) : h("p", { class: "empty" }, "Nothing to do.")),
      section("THE HUMAN", h("p", null, "You push and merge. Tech Support never pushes, merges or changes owner-only files unless you ask."))]);
  }
  function supportPage() {
    const all = incList(), needs = all.filter(function (i) { return i.status === "needs_owner"; });
    return [head("monitor → tech support", "TECH SUPPORT"), supportBanner(),
      h("div", { class: "grid stats" },
        stat("OPEN INCIDENTS", String(openInc().length), openInc().length ? "see below" : "all clear", openInc().length ? "bad" : ""),
        stat("FIX READY TO SHIP", String(fixReady().length), "verified, waiting for you", fixReady().length ? "warn" : ""),
        stat("NEEDS YOUR DECISION", String(needs.length), "owner-only or stuck"),
        stat("RESOLVED", String(all.filter(function (i) { return i.status === "resolved"; }).length), "all time")),
      panel("HOW A PROBLEM IS HANDLED", stageBar(-1),
        h("p", { class: "empty" }, "The monitor flags a failing check and raises it. Tech Support (Claude) diagnoses it and proposes a fix. The fix is tested in a scratch copy, applied on a branch, and checked again in your working tree. You push the branch and merge it. After you pull it down, the fix is verified once more and the incident closes."),
        copyBtn("python3 scripts/techsupport.py detect", "Copy: run the health checks"), copyBtn("python3 scripts/techsupport.py status", "Copy: list incidents")),
      panel("INCIDENTS", table(["ID", "Check", "Problem", "Severity", "Status"], all.map(function (i) {
        return { data: i, cells: [i.id, i.check, i.title, pill(i.severity, i.severity === "high" ? "bad" : "warn"), pill(i.status.replace(/_/g, " "), incCls[i.status])] };
      }), incidentDrawer, "No incidents. Run the health checks to look for problems."))];
  }

  /* ---------- approvals (needs scripts/dashboard_server.py) ---------- */
  let RES = null, TOKEN = null;
  const jget = function (path) { return fetch(path, { cache: "no-store" }).then(function (r) { return r.json(); }); };
  function badge() {
    const n = RES ? RES.counts.awaiting_approval : 0, el = document.getElementById("appr-badge");
    if (el) { el.textContent = n ? String(n) : ""; el.style.display = n ? "inline-block" : "none"; }
  }
  function loadResearch() {
    return jget("/api/research").then(function (j) { RES = j; badge(); return j; }).catch(function () { RES = null; return null; });
  }
  function post(path, body) {
    const tok = TOKEN ? Promise.resolve(TOKEN) : jget("/api/token").then(function (t) { TOKEN = t.token; return TOKEN; });
    return tok.then(function (t) {
      return fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Dash-Token": t }, body: JSON.stringify(body) }).then(function (r) { return r.json(); });
    });
  }
  const CHECKS = { stock_in_hand: "The stock is in my hands", supplier_agreement: "I have a supplier agreement", brand_authorised: "I may sell this brand",
    safety_docs_ok: "Safety marking and documents checked", delivery_promise_checked: "The delivery time I will state is one I can meet",
    pre_contract_info_ok: "Trader, total price and cancellation terms are clear", returns_process_ok: "Returns process decided", ad_claims_checked: "Ad claims checked (CAP Code)",
    platform_policy_checked: "Platform shop rules checked" };
  const gbpn = function (n) { return n == null ? "—" : "£" + Number(n).toFixed(2); };
  function thumb(it) {
    const img = (it.market.images || []).find(function (i) { return i.url_local; });
    return img ? h("img", { class: "thumb", src: img.url_local, alt: "" }) : h("div", { class: "thumb none" }, "no image");
  }
  function verdictChips(it) {
    return ["listings", "pricing", "compliance", "finance"].map(function (a) {
      const v = (it.agent_notes[a] || {}).verdict;
      return chip(a + ": " + (v || "waiting"), v === "block" ? "bad" : "");
    });
  }
  function productDrawer(it) {
    const m = it.margin || {}, sup = it.supplier, mk = it.market, flags = (it.policy ? it.policy.results : []).filter(function (r) { return r.status === "flag"; });
    const blocks = (it.policy ? it.policy.results : []).filter(function (r) { return r.status === "block"; });
    const reason = h("textarea", { rows: "2", placeholder: "Reason (kept as a lesson if you deny)", class: "filter" });
    const ack = h("input", { type: "checkbox", id: "ack" });
    const msg = h("p", { class: "empty" });
    const decide = function (d) {
      post("/api/decision", { id: it.id, decision: d, reason: reason.value, acknowledge: ack.checked }).then(function (r) {
        msg.textContent = r.message;
        if (r.ok) { loadResearch().then(function () { closeDrawer(); render(); }); }
      });
    };
    const gal = h("div", { class: "gallery" }, (mk.images || []).filter(function (i) { return i.url_local; }).map(function (i) { return h("a", { href: i.url_local, target: "_blank", rel: "noopener" }, h("img", { src: i.url_local, alt: "" })); }));
    const ln = (it.agent_notes.listings || {}).data || {}, pr = (it.agent_notes.pricing || {}).data || {};
    const link = function (label, url) { return url ? h("p", null, label + ": ", h("a", { href: url, target: "_blank", rel: "noopener noreferrer" }, url)) : h("p", { class: "empty" }, label + ": none"); };
    drawer(it.id, it.title, [
      h("div", { class: "badges" }, pill(it.channel), pill(it.fulfilment_model.replace(/_/g, " ")), pill(it.stage.replace(/_/g, " "), it.stage === "awaiting_approval" ? "warn" : "mut")),
      gal.children.length ? section("IMAGES (analysis only, rights unverified)", gal) : null,
      section("LINKS", h("div", null, link("eBay listing", mk.url), link("Supplier (" + sup.platform + ")", sup.url))),
      section("MARGIN", h("div", null, h("p", null, (m.margin_pct != null ? m.margin_pct + "% margin" : "no margin yet") + " at " + gbpn(it.suggested_price_gbp || mk.price_gbp) +
        " (if costs rose " + (m.stress_cost_increase_pct || 0) + "%: " + (m.stress_margin_pct != null ? m.stress_margin_pct + "%" : "—") + ")"),
        h("p", { class: "empty" }, "Item " + gbpn(m.cost_gbp) + ", supplier shipping " + gbpn(m.shipping_gbp) + ", postage " + gbpn(m.postage_gbp) + ", packaging " + gbpn(m.packaging_gbp) +
          ", fees " + gbpn(m.channel_fees_gbp) + ", returns allowance " + gbpn(m.returns_allowance_gbp) + (m.fees_confirmed ? "" : ". Fee figures are placeholders.")))),
      section("MARKET AND SUPPLIER", h("p", null, "Sold in 30 days: " + (mk.sold_30d == null ? "—" : mk.sold_30d) + " | Competing listings: " + (mk.active_listings == null ? "—" : mk.active_listings) +
        " | Supplier delivery up to " + sup.delivery_days_max + " days | Rating " + sup.rating + " | Ships from " + sup.ships_from)),
      (mk.review_themes || []).length ? section("BAD-REVIEW THEMES", h("div", { class: "chips" }, mk.review_themes.map(function (t) { return chip(t); }))) : null,
      ln.improved_title ? section("LISTING SUGGESTION", h("div", null, h("p", null, h("b", null, ln.improved_title)), h("p", null, ln.improved_description || ""),
        h("ul", null, (ln.key_points || []).map(function (k) { return h("li", null, k); })))) : null,
      pr.suggested_price_gbp ? section("PRICE SUGGESTION", h("p", null, gbpn(pr.suggested_price_gbp) + ". " + (pr.reasoning || ""))) : null,
      section("COMPLIANCE GATE: " + (it.policy ? it.policy.overall.toUpperCase() : "not run"), h("div", null,
        blocks.map(function (r) { return h("p", { class: "mono" }, "BLOCK " + r.id + " " + r.title + (r.detail ? " (" + r.detail + ")" : "")); }),
        flags.map(function (r) { return h("p", { class: "empty" }, "FLAG " + r.id + " " + r.title + (r.detail ? " (" + r.detail + ")" : "")); }),
        !blocks.length && !flags.length ? h("p", { class: "empty" }, "No flags.") : null)),
      section("AGENT REVIEWS", h("div", { class: "chips" }, verdictChips(it))),
      section("YOUR CHECKS", h("div", { class: "checks" }, RES.confirmable.map(function (f) {
        const box = h("input", { type: "checkbox" });
        box.checked = !!it[f];
        box.addEventListener("change", function () { post("/api/confirm", { id: it.id, field: f, value: box.checked }).then(function () { loadResearch(); }); });
        return h("label", null, box, " " + (CHECKS[f] || f));
      }))),
      it.stage === "awaiting_approval" ? section("YOUR DECISION", h("div", null, reason,
        h("label", null, ack, " I have read the flags above and accept them"),
        h("div", null, h("button", { class: "btn good", type: "button", onclick: function () { decide("approved"); } }, "Approve"),
          h("button", { class: "btn badbtn", type: "button", onclick: function () { decide("denied"); } }, "Deny")),
        h("p", { class: "empty" }, "Approve creates a launch pack and a sample-order checklist. It does not buy or list anything."), msg)) :
        section("STATUS", h("p", { class: "empty" }, it.reject_reason || (it.history[it.history.length - 1] || {}).note || it.stage))]);
  }
  function approvalsBody(j) {
    if (!j) {
      return [h("div", { class: "banner stopped" }, h("b", null, "The approval buttons need the dashboard server.")),
        h("p", { class: "empty" }, "Stop the current server (Ctrl+C) and run this instead. It serves the same dashboard and saves your decisions:"),
        copyBtn("python3 scripts/dashboard_server.py", "Copy command")];
    }
    const c = j.counts, by = function (s) { return j.items.filter(function (i) { return i.stage === s; }); };
    const card = function (it) {
      const m = it.margin || {}, flags = (it.policy ? it.policy.results : []).filter(function (r) { return r.status === "flag"; }).length;
      return h("button", { class: "pcard", type: "button", onclick: function () { productDrawer(it); } }, thumb(it),
        h("div", null, h("b", null, it.title), h("div", { class: "chips" }, chip(it.channel), chip(it.fulfilment_model.replace(/_/g, " "))),
          h("p", { class: "empty" }, (m.margin_pct != null ? m.margin_pct + "% margin · " : "") + gbpn(it.suggested_price_gbp || it.market.price_gbp) + " · delivery ≤ " + it.supplier.delivery_days_max + " days · " + flags + " flag(s)"),
          h("div", { class: "chips" }, verdictChips(it))));
    };
    const rows = function (list, cols) {
      return table(cols, list.map(function (it) { return { data: it, cells: [it.id, it.title, it.channel, it.reject_reason || (it.history[it.history.length - 1] || {}).note || ""] }; }), productDrawer, "None.");
    };
    return [h("div", { class: "grid stats" }, stat("AWAITING YOUR DECISION", String(c.awaiting_approval), "all four reviews in", c.awaiting_approval ? "warn" : ""),
        stat("IN PROGRESS", String(c.analysed + c.blocked), "reviews pending or blocked"), stat("APPROVED", String(c.approved), "launch pack made"),
        stat("DENIED", String(c.denied), "kept as lessons"), stat("REJECTED BY RULES", String(c.rejected), "reason kept")),
      j.stale_rules.length ? h("div", { class: "banner warning" }, h("b", null, "Compliance rules need a review"), h("span", null, j.stale_rules.join(" "))) : null,
      panel("AWAITING YOUR DECISION", by("awaiting_approval").length ? h("div", { class: "pcards" }, by("awaiting_approval").map(card)) : h("p", { class: "empty" }, "Nothing waiting. Import products with: python3 scripts/research.py import FILE.csv")),
      panel("IN PROGRESS", rows(by("analysed").concat(by("blocked")), ["ID", "Product", "Channel", "Next / reason"])),
      panel("REJECTED BY THE RULES", rows(by("rejected"), ["ID", "Product", "Channel", "Reason"])),
      panel("DECIDED", rows(by("approved").concat(by("denied")), ["ID", "Product", "Channel", "Outcome"]))];
  }
  function approvalsPage() {
    const box = h("div", null, h("p", { class: "empty" }, "Loading..."));
    loadResearch().then(function (j) { box.replaceChildren.apply(box, approvalsBody(j).filter(Boolean)); });
    return [head("product research", "APPROVALS"), box];
  }

  /* ---------- operations: alerts, parcels, profit and loss, social and shop figures (needs scripts/dashboard_server.py) ---------- */
  let OPS = null;
  function opsBadge() {
    const n = OPS ? OPS.alerts.filter(function (a) { return a.status === "open"; }).length : 0, el = document.getElementById("ops-badge");
    if (el) { el.textContent = n ? String(n) : ""; el.style.display = n ? "inline-block" : "none"; }
  }
  function loadOps() {
    return fetch("/api/ops", { cache: "no-store" }).then(function (r) { return r.json(); }).then(function (j) { OPS = j.error ? null : j; opsBadge(); return OPS; }).catch(function () { OPS = null; return null; });
  }
  const sevColour = { critical: "#ff4d6d", warning: "#fbbf24", info: "#38bdf8" };
  const pct = function (n) { return (n == null ? "—" : n) + "%"; };
  function opsBody(o) {
    if (!o) {
      return [h("div", { class: "banner stopped" }, h("b", null, "The operations figures need the dashboard server.")),
        h("p", { class: "empty" }, "Stop the current server (Ctrl+C) and run this instead:"), copyBtn("python3 scripts/dashboard_server.py", "Copy command")];
    }
    const noop = function () {}, fun = o.funnel, open = o.alerts.filter(function (a) { return a.status === "open"; });
    const alerts = o.alerts.length ? o.alerts.map(function (a) {
      const ack = function (status) { post("/api/alert", { id: a.id, status: status }).then(function () { loadOps().then(render); }); };
      return h("div", { class: "check" }, h("span", { class: "dot off", style: "background:" + sevColour[a.severity] }),
        h("div", { style: "flex:1" }, h("b", null, a.severity.toUpperCase() + " · " + a.kind.replace(/_/g, " ") + (a.status === "acknowledged" ? " · acknowledged" : "")), h("small", null, a.message)),
        a.status === "open" ? h("button", { class: "btn", type: "button", onclick: function () { ack("acknowledged"); } }, "Acknowledge") : null,
        h("button", { class: "btn", type: "button", onclick: function () { ack("closed"); } }, "Close"));
    }) : h("p", { class: "empty" }, "Nothing needs you right now.");
    const weeks = o.pnl.weekly.slice().reverse(), thisWeek = weeks[0] || { spend: 0, revenue: 0, refunds: 0, profit: 0 };
    return [h("div", { class: "grid stats" },
        stat("OPEN ALERTS", String(open.length), open.filter(function (a) { return a.severity === "critical"; }).length + " critical", open.length ? "warn" : ""),
        stat("PARCELS LATE", String(o.shipments.filter(function (s) { return s.days_late > 0; }).length), "of " + o.shipments.filter(function (s) { return s.status !== "delivered"; }).length + " on the way"),
        stat("THIS WEEK PROFIT", gbp(thisWeek.profit), "spent " + gbp(thisWeek.spend) + " · earned " + gbp(thisWeek.revenue - thisWeek.refunds), thisWeek.profit < 0 ? "bad" : ""),
        stat("CART ABANDONMENT", pct(fun.abandonment_pct), fun.abandoned_checkouts + " of " + fun.checkouts + " checkouts · last " + o.window_days + " days")),
      panel("ALERTS · WHAT NEEDS YOU", h("div", null, alerts)),
      panel("DELIVERIES · CHECKED EVERY DAY", table(["Parcel", "Order", "Carrier", "Tracking", "Due", "Status", "Late"],
        o.shipments.map(function (s) { return { data: s, cells: [s.id, s.order_id, s.carrier || "—", s.tracking_no || "none", s.due || "—", s.status.replace(/_/g, " "), s.days_late ? s.days_late + " day(s)" : ""] }; }), noop, "No parcels recorded yet.")),
      panel("PROFIT AND LOSS · WEEK BY WEEK", table(["Week from", "Orders", "Earned", "Spent", "Profit", "Ads", "AI"],
        weeks.map(function (w) { return { data: w, cells: [w.week_start, String(w.orders), gbp(w.revenue - w.refunds), gbp(w.spend), gbp(w.profit), gbp(w.ads), gbp(w.ai)] }; }), noop, "No orders yet."),
        h("p", { class: "empty" }, "Earned is sales minus refunds. Spent is supplier cost, postage, fees, ads and AI." + (o.pnl.fees_estimated_orders ? " Fees were estimated for " + o.pnl.fees_estimated_orders + " order(s) from placeholder rates." : ""))),
      panel("PROFIT AND LOSS · DAY BY DAY", table(["Date", "Orders", "Revenue", "Costs", "Profit"],
        o.pnl.daily.slice().reverse().map(function (d) { return { data: d, cells: [d.date, String(d.orders), gbp(d.revenue), gbp(d.cogs + d.fees + d.ads + d.ai), gbp(d.profit)] }; }), noop, "No data.")),
      panel("PRICE WATCH · SUPPLIER COST AGAINST YOUR MARGIN", table(["Product", "Channel", "Price", "Cost now", "Margin", ""],
        o.listings.map(function (l) { return { data: l, cells: [l.title || l.product_id, l.channel, gbp(l.price_gbp), gbp(l.cost_now_gbp) + (l.cost_now_gbp > l.cost_assumed_gbp ? " (was " + gbp(l.cost_assumed_gbp) + ")" : ""), pct(l.margin_pct), l.ok ? "OK" : "BELOW " + o.min_margin_pct + "%"] }; }), noop, "No live listings recorded yet.")),
      panel("SOCIAL ENGAGEMENT · LAST " + o.window_days + " DAYS", table(["Platform", "Posts", "Impressions", "Reach", "Likes", "Comments", "Shares", "Saves", "Clicks", "Engagement"],
        o.social.map(function (s) { return { data: s, cells: [s.platform, String(s.posts), String(s.impressions), String(s.reach), String(s.likes), String(s.comments), String(s.shares), String(s.saves), String(s.clicks), pct(s.engagement_pct)] }; }), noop, "No social figures yet. Import a platform export: python3 scripts/watch.py metrics import FILE.csv")),
      panel("SHOP · SESSIONS TO ORDERS · LAST " + o.window_days + " DAYS", h("div", { class: "grid stats" },
        stat("SESSIONS", String(fun.sessions), ""), stat("ADDED TO CART", String(fun.carts), ""), stat("STARTED CHECKOUT", String(fun.checkouts), ""), stat("ORDERS", String(fun.orders), pct(fun.conversion_pct) + " of sessions"),
        stat("ABANDONED", String(fun.abandoned_checkouts), pct(fun.abandonment_pct) + " of checkouts", fun.abandonment_pct > 70 ? "warn" : ""), stat("REVENUE", gbp(fun.revenue_gbp), "from the shop"))),
      panel("CUSTOMER MESSAGES · DRAFTS WAITING FOR YOU", h("div", null,
        h("p", { class: "empty" }, o.inbox.awaiting_approval + " draft(s) waiting · " + (o.inbox.needs_reply || 0) + " with no template · " + o.inbox.escalated + " escalated · " + o.inbox.open + " open. Approve with: python3 scripts/inbox.py approve ID"),
        o.inbox.items.length ? o.inbox.items.map(function (i) {
          return h("div", { class: "decision" }, h("b", null, i.platform + " " + i.kind + " · " + i.category), h("div", { class: "empty" }, "Customer: " + i.message), h("div", null, i.draft ? "Draft: " + i.draft : i.reason),
            i.missing_facts.length ? pill("needs facts: " + i.missing_facts.join(", "), "warn") : i.draft ? pill("ready for your approval", "ok") : pill("needs a reply written", "warn"), h("div", { class: "empty mono" }, i.id));
        }) : null))];
  }
  function opsPage() {
    const box = h("div", null, h("p", { class: "empty" }, "Loading..."));
    loadOps().then(function (o) { box.replaceChildren.apply(box, opsBody(o).filter(Boolean)); });
    return [head("deliveries, money and customers", "OPERATIONS"), box];
  }

  /* ---------- shell ---------- */
  const NAV = [["OPERATE", [["home", "Home"], ["approvals", "Approvals"], ["ops", "Operations"], ["tasks", "Tasks"], ["support", "Tech Support"], ["finances", "Finances"]]], ["AGENTS", [["agents", "Agents"], ["org", "Org Chart"]]],
    ["INTELLIGENCE", [["core", "Knowledge Core"], ["health", "Health"]]], ["SYSTEM", [["connections", "Connections"], ["roadmap", "Roadmap"]]]];
  const PAGES = { home: home, tasks: tasksPage, approvals: approvalsPage, ops: opsPage, support: supportPage, finances: financesPage, agents: agentsPage, org: orgPage, core: corePage, health: healthPage, connections: connectionsPage, roadmap: roadmapPage };

  function side(active) {
    const live = D.agents.filter(function (a) { return a.enabled && a.mode === "api"; }).length;
    const nav = h("nav", { class: "nav" });
    NAV.forEach(function (g) {
      nav.append(h("div", { class: "navh" }, g[0]));
      g[1].forEach(function (p) {
        nav.append(h("a", { href: "#" + p[0], class: p[0] === active ? "on" : "" }, p[1],
          p[0] === "approvals" ? h("span", { class: "nav-badge", id: "appr-badge", style: "display:none" }) : p[0] === "ops" ? h("span", { class: "nav-badge", id: "ops-badge", style: "display:none" }) : null));
      });
    });
    document.getElementById("side").replaceChildren(
      h("div", { class: "logo" }, h("i"), h("div", null, h("b", null, "COMMERCE OS"), h("span", null, "V1 · OPERATOR MODE"))), nav,
      h("div", { class: "sidefoot" }, h("div", null, h("span", { class: live ? "dot" : "dot off" }), live + "/" + D.agents.length + " agents on the API"),
        h("div", null, "static page · reads status.js")));
  }
  function render() {
    const view = document.getElementById("view");
    if (!D) { view.textContent = "No data yet. Run: python3 scripts/build_dashboard.py"; return; }
    const parts = (location.hash.slice(1) || "home").split("/"), page = PAGES[parts[0]] ? parts[0] : "home";
    view.replaceChildren();
    add(view, [PAGES[page](parts[1])]);
    side(page);
    closeDrawer();
  }
  window.addEventListener("hashchange", render);
  render();
  loadResearch();
  loadOps();
})();
