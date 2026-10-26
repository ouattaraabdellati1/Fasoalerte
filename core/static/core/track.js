(function () {
  "use strict";
  var STEPS = ["Signalement transmis et chiffré", "Réception centre de commandement", "Vérification et affectation patrouille", "Clôture du dossier"];
  var err = document.getElementById("terr");
  function showErr(m) { err.textContent = m; err.hidden = !m; }

  function render(d) {
    document.getElementById("result").hidden = false;
    document.getElementById("rcode").textContent = d.tracking_code;
    document.getElementById("rcat").textContent = d.category_label;
    document.getElementById("rcity").textContent = d.city || "—";
    document.getElementById("rdate").textContent = new Date(d.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
    document.getElementById("runit").textContent = d.assigned_unit;
    document.getElementById("runitrow").hidden = !d.assigned_unit;
    document.getElementById("rstep").textContent = "Étape " + d.status + " sur 4";
    var notes = {}; d.events.forEach(function (e) { notes[e.status] = e; });
    var ol = document.getElementById("steps"); ol.textContent = "";
    STEPS.forEach(function (label, i) {
      var n = i + 1, cls = n < d.status || d.status === 4 ? "done" : n === d.status ? "cur" : "";
      var kids = [FA.el("b", { text: label })];
      if (notes[n]) {
        if (notes[n].note) kids.push(FA.el("small", { text: notes[n].note }));
        kids.push(FA.el("small", { text: new Date(notes[n].at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) }));
      }
      ol.appendChild(FA.el("li", { class: cls }, kids));
    });
    document.getElementById("official").hidden = !d.official_message;
    document.getElementById("otext").textContent = d.official_message;
  }

  function lookup(code) {
    code = code.trim().toUpperCase(); showErr("");
    if (!/^FA-[A-Z]{2,5}-[A-Z2-9]{8}$/.test(code)) return showErr("Code invalide. Exemple : FA-OUAGA-ABCD2345");
    fetch("/api/reports/" + encodeURIComponent(code) + "/").then(function (r) {
      if (r.status === 404) throw new Error("Dossier introuvable. Vérifiez le code.");
      if (r.status === 429) throw new Error("Trop de recherches. Réessayez plus tard.");
      if (!r.ok) throw new Error("Erreur du serveur.");
      return r.json();
    }).then(render).catch(function (e) { showErr(e.message === "Failed to fetch" ? "Pas de connexion." : e.message); });
  }

  function history() {
    var l = FA.get("fa_codes", []), box = document.getElementById("hist"), ul = document.getElementById("histlist");
    ul.textContent = ""; box.hidden = !l.length;
    l.forEach(function (x) {
      var b = FA.el("button", { type: "button", text: x.code });
      b.addEventListener("click", function () { document.getElementById("tcode").value = x.code; lookup(x.code); window.scrollTo(0, 0); });
      ul.appendChild(FA.el("li", {}, [b, FA.el("small", { class: "muted", text: new Date(x.at).toLocaleDateString("fr-FR") })]));
    });
  }

  document.getElementById("tf").addEventListener("submit", function (e) { e.preventDefault(); lookup(document.getElementById("tcode").value); });
  document.getElementById("wipe").addEventListener("click", function () {
    if (!confirm("Effacer tous les codes et copies hors-ligne de cet appareil ?")) return;
    try { localStorage.clear(); sessionStorage.clear(); } catch (e) {}
    if (window.caches) caches.keys().then(function (ks) { ks.forEach(function (k) { caches.delete(k); }); });
    document.getElementById("result").hidden = true; history(); showErr("Historique effacé sur cet appareil.");
  });

  history();
  var q = new URLSearchParams(location.search).get("code");
  if (q) { document.getElementById("tcode").value = q; lookup(q); }
})();
