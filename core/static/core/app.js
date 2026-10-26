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

  var page = document.body.getAttribute("data-page");
  document.querySelectorAll(".tabs a").forEach(function (a) {
    if (a.getAttribute("data-p") === page) a.classList.add("active");
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () { navigator.serviceWorker.register("/sw.js").catch(function () {}); });
  }
})();
