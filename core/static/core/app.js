/* Utilitaires partagés. Règle d'or : on n'utilise JAMAIS innerHTML avec des données reçues
   (textContent uniquement) -> pas de faille XSS. */
(function () {
  "use strict";
  var FA = (window.FA = {});

  FA.el = function (tag, props, children) {
    var e = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      if (k === "text") e.textContent = props[k];
      else if (k === "class") e.className = props[k];
      else e.setAttribute(k, props[k]);
    });
    (children || []).forEach(function (c) { e.appendChild(c); });
    return e;
  };

  // Stockage local : protégé par try/catch (navigation privée, stockage bloqué…)
  FA.get = function (k, def) {
    try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : def; } catch (e) { return def; }
  };
  FA.set = function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };

  FA.addCode = function (code, category) {
    var l = FA.get("fa_codes", []).filter(function (x) { return x.code !== code; });
    l.unshift({ code: code, category: category || "", at: Date.now() });
    FA.set("fa_codes", l.slice(0, 30));
  };

  // GET avec copie locale : si le réseau est absent, on sert la dernière copie.
  FA.cachedGet = function (url) {
    return fetch(url, { headers: { Accept: "application/json" } })
      .then(function (r) { if (!r.ok) throw new Error("http"); return r.json(); })
      .then(function (d) { FA.set("fa_cache:" + url, { at: Date.now(), d: d }); return { data: d, offline: false }; })
      .catch(function () {
        var c = FA.get("fa_cache:" + url, null);
        if (!c) throw new Error("none");
        return { data: c.d, offline: true, at: c.at };
      });
  };

  // File d'attente hors-ligne (signalements SANS fichiers) : envoi dès le retour du réseau.
  FA.queueAdd = function (fields) {
    var q = FA.get("fa_queue", []); q.push(fields); FA.set("fa_queue", q);
  };
  FA.flushQueue = function () {
    var q = FA.get("fa_queue", []);
    if (!q.length || !navigator.onLine) return;
    var item = q[0], fd = new FormData();
    Object.keys(item).forEach(function (k) { fd.append(k, item[k]); });
    fetch("/api/reports/", { method: "POST", body: fd })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) { FA.addCode(d.tracking_code, item.category); FA.set("fa_queue", FA.get("fa_queue", []).slice(1)); FA.flushQueue(); })
      .catch(function (s) { if (s === 400) { FA.set("fa_queue", FA.get("fa_queue", []).slice(1)); FA.flushQueue(); } });
  };

  function net() {
    var on = navigator.onLine;
    var d = document.getElementById("netdot"), t = document.getElementById("nettext");
    if (d) d.className = "dot" + (on ? "" : " off");
    if (t) t.textContent = on ? "Réseau actif" : "Hors-ligne";
    if (on) FA.flushQueue();
  }
  window.addEventListener("online", net); window.addEventListener("offline", net); net();


  // ---------- Rendus partagés ----------
  FA.fmtF = function (n) { return Number(n).toLocaleString("fr-FR") + " F"; };

  FA.priceRows = function (box, data) {
    box.textContent = "";
    if (!data.length) { box.appendChild(FA.el("p", { class: "muted pad", text: "Aucun prix publié." })); return; }
    data.forEach(function (p) {
      var left = FA.el("div", { class: "pl" }, [FA.el("div", { class: "n", text: p.product }), FA.el("div", { class: "u", text: p.unit })]);
      var right = [FA.el("div", { class: "v", text: FA.fmtF(p.max_price_fcfa) }), FA.el("span", { class: "pbadge", text: "Plafond" })];
      if (p.previous_price_fcfa) right.splice(1, 0, FA.el("div", { class: "o", text: "avant " + FA.fmtF(p.previous_price_fcfa) }));
      box.appendChild(FA.el("div", { class: "prow" }, [left, FA.el("div", { class: "pr" }, right)]));
    });
  };

  function share(it) {
    var text = it.title + " – " + it.summary, url = location.origin + "/";
    if (navigator.share) { navigator.share({ title: it.title, text: text, url: url }).catch(function () {}); return; }
    if (navigator.clipboard) navigator.clipboard.writeText(text + " " + url).then(function () { alert("Texte copié : collez-le dans WhatsApp ou SMS."); });
  }

  FA.feedCard = function (it) {
    var verified = it.kind === "info" && it.category === "verif";
    var head, body = [], foot;
    if (it.kind === "rumor") {
      head = [FA.el("span", { class: "bd rum", text: "⊗ Alerte Rumeur" }), FA.el("span", { class: "tm", text: FA.ago(it.published_at) }),
              FA.el("span", { class: "rg red", text: it.rumor_label || "" })];
      body.push(FA.el("h3", { text: it.title }));
      body.push(FA.el("div", { class: "box warn", text: "⚠ " + it.summary }));
      if (it.fact_real) body.push(FA.el("div", { class: "box fact" }, [FA.el("b", { text: "Le Fait Réel : " }), document.createTextNode(it.fact_real)]));
      var rel = FA.el("a", { class: "pillbtn soft", href: "/signaler/?cat=fraude_prix", text: "Signaler un relais" });
      foot = [FA.el("span", { class: "fsrc", text: "Source : " + it.source }), rel];
    } else if (verified) {
      head = [FA.el("span", { class: "bd ok", text: "✔ Élément authentifié" }), FA.el("span", { class: "tm", text: FA.ago(it.published_at) })];
      body.push(FA.el("h3", { text: it.title }));
      body.push(FA.el("div", { class: "box good" }, [FA.el("b", { text: "Précision officielle : " }), document.createTextNode(it.summary)]));
      foot = [FA.el("span", { class: "fsrc", text: "Source : " + it.source })];
    } else {
      head = [FA.el("span", { class: "bd ok", text: "✔ " + it.source }), FA.el("span", { class: "tm", text: FA.ago(it.published_at) }),
              FA.el("span", { class: "rg", text: it.region_label || "" })];
      body.push(FA.el("h3", { text: it.title }));
      body.push(FA.el("p", { text: it.summary }));
      if (it.image_url) body.push(FA.el("img", { class: "fimg", src: it.image_url, alt: "", loading: "lazy" }));
      var sh = FA.el("button", { type: "button", class: "linkbtn", text: "↗ Diffuser" });
      sh.addEventListener("click", function () { share(it); });
      foot = [FA.el("span", { class: "fsrc", text: it.attested ? "✔ Attesté" : "" }), sh];
    }
    return FA.el("article", { class: "fcard" }, [FA.el("div", { class: "fhead" }, head)].concat(body, [FA.el("div", { class: "ffoot" }, foot)]));
  };

  // Cloche : nombre d'alertes actives, lien vers la plus récente
  FA.ago = function (iso) {
    var m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
    if (m < 1) return "à l'instant";
    if (m < 60) return "Il y a " + m + " min";
    if (m < 1440) return "Il y a " + Math.round(m / 60) + " h";
    return "Il y a " + Math.round(m / 1440) + " j";
  };
  FA.cachedGet("/api/alerts/").then(function (r) {
    var b = document.getElementById("bell"); if (!b || !r.data.length) return;
    document.getElementById("bellN").textContent = r.data.length;
    b.href = "/alerte/" + r.data[0].id + "/"; b.hidden = false;
  }).catch(function () {});

  var page = document.body.getAttribute("data-page");
  document.querySelectorAll(".tabs a").forEach(function (a) {
    if (a.getAttribute("data-p") === page) a.classList.add("active");
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  }
})();
