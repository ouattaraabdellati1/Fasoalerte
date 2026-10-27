(function () {
  "use strict";
  FA.cachedGet("/api/prices/").then(function (r) { FA.priceRows(document.getElementById("uprices"), r.data); })
    .catch(function () { document.getElementById("uprices").textContent = "Prix indisponibles (aucune connexion et aucune copie)."; });
  FA.cachedGet("/api/feed/?category=verif").then(function (r) {
    var box = document.getElementById("rumors"); box.textContent = "";
    if (!r.data.length) { box.appendChild(FA.el("p", { class: "muted pad", text: "Aucun démenti publié." })); return; }
    r.data.forEach(function (i) { box.appendChild(FA.feedCard(i)); });
  }).catch(function () { document.getElementById("rumors").textContent = "Indisponible hors-ligne."; });
})();
