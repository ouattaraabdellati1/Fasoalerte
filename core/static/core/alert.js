(function () {
  "use strict";
  var m = location.pathname.match(/\/alerte\/(\d+)\//); if (!m) { location.href = "/"; return; }
  var id = m[1];
  var TAG = { max: "DÉCRET / ALERTE MAXIMALE", important: "ALERTE IMPORTANTE", info: "INFORMATION OFFICIELLE" };
  var LANG = [["moore", "Mooré"], ["dioula", "Dioula"], ["fulfulde", "Fulfuldé"], ["francais", "Français"]];
  function $(i) { return document.getElementById(i); }

  FA.cachedGet("/api/alerts/" + id + "/").then(function (r) {
    var a = r.data;
    $("atag").textContent = TAG[a.level] || "ALERTE";
    $("atitle").textContent = a.title;
    $("amsg").textContent = a.message;
    $("afull").textContent = a.full_text || "";
    $("asrc").textContent = (a.source ? "Source : " + a.source + " · " : "") + new Date(a.published_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
    $("acanal").textContent = "Canal National #" + a.id;
    $("acard").classList.add("lv-" + a.level);
    $("asms").setAttribute("href", "sms:?&body=" + encodeURIComponent(a.title + " – " + a.message + " (FasoAlerte)"));

    // Voix en langues
    var any = Object.keys(a.audio || {}).length, grid = $("vgrid"), player = $("aplayer"), cur = null;
    $("avoice").hidden = !any;
    LANG.forEach(function (l) {
      var url = (a.audio || {})[l[0]];
      var b = FA.el("button", { type: "button", class: "vbtn", text: (url ? "▶ " : "") + l[1] });
      if (!url) { b.disabled = true; b.appendChild(FA.el("small", { text: "bientôt" })); }
      else b.addEventListener("click", function () {
        if (cur === b && !player.paused) { player.pause(); return; }
        document.querySelectorAll(".vbtn.on").forEach(function (x) { x.classList.remove("on"); });
        player.src = url; player.play().catch(function () {}); b.classList.add("on"); cur = b;
      });
      grid.appendChild(b);
    });

    // Mercuriale (si l'alerte la demande)
    if (a.show_prices) FA.cachedGet("/api/prices/").then(function (p) {
      $("aprices").hidden = false; var box = $("aplist"); box.textContent = "";
      p.data.forEach(function (x) {
        var right = [FA.el("div", { class: "nv", text: FA.fmtF(x.max_price_fcfa) }), FA.el("div", { class: "plaf", text: "PLAFOND LÉGAL" })];
        var left = [FA.el("b", { text: x.product }), FA.el("small", { text: x.unit })];
        if (x.previous_price_fcfa && x.previous_price_fcfa > x.max_price_fcfa) {
          var pct = Math.round((x.previous_price_fcfa - x.max_price_fcfa) / x.previous_price_fcfa * 100);
          left.push(FA.el("span", { class: "old", text: FA.fmtF(x.previous_price_fcfa) }));
          left.push(FA.el("span", { class: "pct", text: "-" + pct + " %" }));
        }
        box.appendChild(FA.el("div", { class: "arow" }, [FA.el("div", { class: "al" }, left), FA.el("div", { class: "ar" }, right)]));
      });
    }).catch(function () {});
  }).catch(function () {
    $("atitle").textContent = "Alerte introuvable ou expirée";
    $("amsg").textContent = "Cette alerte n'est plus active.";
  });

  var ack = $("aack"), done = FA.get("fa_ack", []);
  if (done.indexOf(Number(id)) >= 0) ack.textContent = "✔ Pris en compte";
  ack.addEventListener("click", function () {
    if (done.indexOf(Number(id)) < 0) { done.push(Number(id)); FA.set("fa_ack", done); }   // accusé gardé sur l'appareil seulement
    location.href = "/";
  });
})();
