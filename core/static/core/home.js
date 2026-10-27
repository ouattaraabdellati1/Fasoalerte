(function () {
  "use strict";
  var LV = { max: "lvl-max", important: "lvl-important", info: "lvl-info" };
  var TAG = { max: "FLASH NATIONAL", important: "ALERTE IMPORTANTE", info: "INFORMATION" };
  var LANG = { moore: "Mooré", dioula: "Dioula", fulfulde: "Fulfuldé", francais: "Français" };
  var items = [], prices = [], cat = "all";

  function stamp() { document.getElementById("stamp").textContent = "Copie hors-ligne"; }

  // ---- Alerte nationale ----
  FA.cachedGet("/api/alerts/").then(function (r) {
    if (r.offline) stamp();
    if (!r.data.length) return;
    var a = r.data[0];
    document.getElementById("hero").className = "hero " + (LV[a.level] || "lvl-info");
    var t = new Date(a.published_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
    document.getElementById("hero-tag").textContent = (TAG[a.level] || "ALERTE") + " • " + t;
    document.getElementById("hero-title").textContent = a.title;
    document.getElementById("hero-msg").textContent = a.message;
    document.getElementById("hero-src").textContent = a.source ? "Source : " + a.source : "";
    document.getElementById("hero-more").href = "/alerte/" + a.id + "/";
    document.getElementById("hero-btns").hidden = false;
    var langs = Object.keys(a.audio || {});
    var play = document.getElementById("hero-play");
    if (!langs.length) { play.hidden = true; return; }
    document.getElementById("hero-audio").hidden = false;
    play.textContent = "▶ Écouter en " + langs.slice(0, 2).map(function (k) { return LANG[k]; }).join(" / ");
    var au = null;
    play.addEventListener("click", function () {
      if (au && !au.paused) { au.pause(); play.textContent = "▶ Écouter en " + langs.slice(0, 2).map(function (k) { return LANG[k]; }).join(" / "); return; }
      au = au || new Audio(a.audio[langs[0]]);
      au.play().catch(function () {}); play.textContent = "⏸ Pause";
      au.onended = function () { play.textContent = "▶ Réécouter"; };
    });
  }).catch(function () {});

  // ---- Fil + mercuriale ----
  function priceCard() {
    var top = prices.slice(0, 3), tiles = FA.el("div", { class: "tiles3" }, top.map(function (p) {
      return FA.el("div", { class: "tile3" }, [FA.el("div", { class: "n", text: p.product }), FA.el("div", { class: "v", text: FA.fmtF(p.max_price_fcfa) }), FA.el("div", { class: "u", text: "Plafond" })]);
    }));
    var rep = FA.el("a", { class: "linkbtn red", href: "/signaler/?cat=fraude_prix", text: "⚠ Signaler un abus" });
    return FA.el("article", { class: "fcard" }, [
      FA.el("div", { class: "fhead" }, [FA.el("span", { class: "bd gold", text: "🏷 Mercuriale des Prix" }), FA.el("span", { class: "tm", text: "Aujourd'hui" }), FA.el("span", { class: "rg", text: "National" })]),
      FA.el("h3", { text: "Prix plafonnés des céréales et denrées de base" }),
      FA.el("p", { text: "Grille officielle en vigueur dans les grands marchés." }), tiles,
      FA.el("div", { class: "ffoot" }, [FA.el("span", { class: "fsrc", text: "Contrôle : Brigade Mobile du Commerce" }), rep])
    ]);
  }
  function draw() {
    var box = document.getElementById("feed"); box.textContent = "";
    var shown = items.filter(function (i) { return cat === "all" || i.category === cat; });
    var n = 0;
    shown.forEach(function (i, idx) {
      box.appendChild(FA.feedCard(i)); n++;
      if (idx === 1 && prices.length && (cat === "all")) { box.appendChild(priceCard()); n++; }
    });
    if (prices.length && (cat === "prix" || (cat === "all" && shown.length < 2))) { box.appendChild(priceCard()); n++; }
    if (!n) box.appendChild(FA.el("p", { class: "muted pad", text: "Aucune information dans cette catégorie pour le moment." }));
    document.querySelector('#filters [data-c="all"]').textContent = "Toutes (" + (items.length + (prices.length ? 1 : 0)) + ")";
  }
  Promise.all([
    FA.cachedGet("/api/feed/").catch(function () { return { data: [] }; }),
    FA.cachedGet("/api/prices/").catch(function () { return { data: [] }; })
  ]).then(function (rs) {
    items = rs[0].data; prices = rs[1].data;
    if (rs[0].offline || rs[1].offline) stamp();
    draw();
  });
  document.getElementById("filters").addEventListener("click", function (e) {
    var b = e.target.closest("button"); if (!b) return;
    cat = b.getAttribute("data-c");
    document.querySelectorAll("#filters button").forEach(function (x) { x.classList.toggle("on", x === b); });
    draw();
  });
})();
