(function () {
  "use strict";
  var LV = { max: "lvl-max", important: "lvl-important", info: "lvl-info" };
  var TAG = { max: "ALERTE MAXIMALE", important: "ALERTE IMPORTANTE", info: "INFORMATION" };
  function fmt(n) { return Number(n).toLocaleString("fr-FR") + " F"; }

  FA.cachedGet("/api/alerts/").then(function (r) {
    var list = r.data; if (!list.length) return;
    var a = list[0], h = document.getElementById("hero");
    h.className = "hero " + (LV[a.level] || "lvl-info");
    document.getElementById("hero-tag").textContent = TAG[a.level] || "ALERTE";
    document.getElementById("hero-title").textContent = a.title;
    document.getElementById("hero-msg").textContent = a.message;
    document.getElementById("hero-src").textContent = (a.source ? "Source : " + a.source + " · " : "") +
      new Date(a.published_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
    if (r.offline) document.getElementById("stamp").textContent = "Copie hors-ligne";
  }).catch(function () {});

  FA.cachedGet("/api/prices/").then(function (r) {
    var box = document.getElementById("prices"); box.textContent = "";
    if (!r.data.length) { box.appendChild(FA.el("p", { class: "muted", text: "Aucun prix publié." })); return; }
    r.data.forEach(function (p) {
      var kids = [FA.el("div", { class: "n", text: p.product }), FA.el("div", { class: "v", text: fmt(p.max_price_fcfa) })];
      if (p.previous_price_fcfa) kids.push(FA.el("div", { class: "o", text: fmt(p.previous_price_fcfa) }));
      kids.push(FA.el("div", { class: "u", text: p.unit + " · plafond" }));
      box.appendChild(FA.el("div", { class: "price" }, kids));
    });
    if (r.offline) document.getElementById("stamp").textContent = "Copie hors-ligne";
  }).catch(function () {
    document.getElementById("prices").textContent = "Prix indisponibles (aucune connexion et aucune copie).";
  });
})();
