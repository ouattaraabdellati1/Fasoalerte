(function () {
  "use strict";
  var f = document.getElementById("f"), errBox = document.getElementById("err");
  var photoBlob = null, audioBlob = null, audioExt = "webm";

  var pre = new URLSearchParams(location.search).get("cat");
  if (pre) { var r = f.querySelector('input[name=category][value="' + pre.replace(/[^a-z_]/g, "") + '"]'); if (r) r.checked = true; }

  function showErr(msg) { errBox.textContent = msg; errBox.hidden = !msg; if (msg) errBox.scrollIntoView({ block: "center" }); }

  // --- GPS ---
  document.getElementById("gps").addEventListener("click", function () {
    var m = document.getElementById("gpsmsg");
    if (!navigator.geolocation) { m.textContent = "GPS non disponible."; return; }
    m.textContent = "Recherche de la position…";
    navigator.geolocation.getCurrentPosition(function (p) {
      f.latitude.value = p.coords.latitude.toFixed(5); f.longitude.value = p.coords.longitude.toFixed(5);
      m.textContent = "Position enregistrée ✔ (précision ≈ " + Math.round(p.coords.accuracy) + " m)";
    }, function () { m.textContent = "Position refusée ou indisponible : indiquez un repère."; },
    { enableHighAccuracy: true, timeout: 15000 });
  });

  // --- Photo : réduite + ré-encodée par le navigateur (efface déjà les métadonnées) ---
  function compress(file) {
    return createImageBitmap(file).then(function (bmp) {
      var max = 1024, s = Math.min(1, max / Math.max(bmp.width, bmp.height));
      var c = document.createElement("canvas"); c.width = Math.round(bmp.width * s); c.height = Math.round(bmp.height * s);
      c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
      return new Promise(function (res) {
        var q = 0.7;
        (function step() {
          c.toBlob(function (b) {
            if (b.size > 100 * 1024 && q > 0.35) { q -= 0.1; step(); } else res(b);
          }, "image/jpeg", q);
        })();
      });
    });
  }
  document.getElementById("photo").addEventListener("change", function (e) {
    var file = e.target.files[0]; if (!file) return;
    compress(file).then(function (b) {
      photoBlob = b;
      var img = document.getElementById("preview"); img.src = URL.createObjectURL(b); img.hidden = false;
      document.getElementById("photolabel").textContent = "📷 Photo prête (" + Math.round(b.size / 1024) + " Ko) – toucher pour changer";
    }).catch(function () { showErr("Photo illisible. Essayez une autre image."); });
  });

  // --- Note vocale (30 s max) ---
  var rec = document.getElementById("rec"), player = document.getElementById("player"), del = document.getElementById("recdel");
  var mr = null, chunks = [], timer = null;
  rec.addEventListener("click", function () {
    if (mr && mr.state === "recording") { mr.stop(); return; }
    if (!navigator.mediaDevices || !window.MediaRecorder) { showErr("L'enregistrement vocal n'est pas disponible sur ce téléphone."); return; }
    navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
      chunks = []; mr = new MediaRecorder(stream);
      mr.ondataavailable = function (e) { if (e.data.size) chunks.push(e.data); };
      mr.onstop = function () {
        clearTimeout(timer); stream.getTracks().forEach(function (t) { t.stop(); });
        var type = mr.mimeType || "audio/webm";
        audioExt = /mp4|aac/.test(type) ? "m4a" : /ogg/.test(type) ? "ogg" : "webm";
        audioBlob = new Blob(chunks, { type: type });
        player.src = URL.createObjectURL(audioBlob); player.hidden = false; del.hidden = false;
        rec.classList.remove("rec"); rec.textContent = "🎙️ Réenregistrer";
      };
      mr.start(); rec.classList.add("rec"); rec.textContent = "⏹ Arrêter l'enregistrement";
      timer = setTimeout(function () { if (mr.state === "recording") mr.stop(); }, 30000);
    }).catch(function () { showErr("Micro refusé. Autorisez-le ou écrivez la description."); });
  });
  del.addEventListener("click", function () { audioBlob = null; player.hidden = true; del.hidden = true; rec.textContent = "🎙️ Enregistrer une note vocale"; });

  // --- Envoi ---
  function messages(d) {
    var out = [];
    (function walk(x) { if (typeof x === "string") out.push(x); else if (x && typeof x === "object") Object.keys(x).forEach(function (k) { walk(x[k]); }); })(d);
    return out.join(" ");
  }
  f.addEventListener("submit", function (ev) {
    ev.preventDefault(); showErr("");
    var cat = f.querySelector("input[name=category]:checked");
    if (!cat) return showErr("Choisissez la nature de l'incident.");
    var hasPlace = f.latitude.value || f.longitude.value || f.location_hint.value.trim();
    if (!hasPlace) return showErr("Indiquez le lieu (GPS ou repère physique).");
    if (!f.description.value.trim() && !audioBlob) return showErr("Ajoutez une description écrite ou vocale.");

    var fields = { category: cat.value, city: f.city.value, location_hint: f.location_hint.value.trim(),
                   latitude: f.latitude.value, longitude: f.longitude.value, description: f.description.value.trim() };
    var fd = new FormData();
    Object.keys(fields).forEach(function (k) { if (fields[k] !== "") fd.append(k, fields[k]); });
    if (photoBlob) fd.append("photo", photoBlob, "photo.jpg");
    if (audioBlob) fd.append("audio", audioBlob, "note." + audioExt);

    var btn = document.getElementById("send"); btn.disabled = true; btn.textContent = "Envoi…";
    fetch("/api/reports/", { method: "POST", body: fd }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) { return { s: r.status, d: d }; });
    }).then(function (x) {
      if (x.s === 201) {
        FA.addCode(x.d.tracking_code, cat.value);
        document.getElementById("code").textContent = x.d.tracking_code;
        document.getElementById("follow").href = "/suivi/?code=" + encodeURIComponent(x.d.tracking_code);
        f.hidden = true; document.getElementById("done").hidden = false; window.scrollTo(0, 0);
      } else if (x.s === 429) showErr("Trop de signalements depuis cette connexion. Réessayez plus tard ou appelez le 1010.");
      else showErr(messages(x.d) || "Signalement refusé.");
    }).catch(function () {
      if (photoBlob || audioBlob) showErr("Pas de connexion. Retirez la photo/le vocal pour l'enregistrer sur l'appareil, ou réessayez plus tard.");
      else { FA.queueAdd(fields); f.hidden = true; var d = document.getElementById("done"); d.hidden = false;
        d.querySelector("h2").textContent = "Enregistré sur l'appareil";
        d.querySelector("p").textContent = "Envoi automatique dès le retour du réseau. Le code de suivi apparaîtra dans l'onglet Suivi.";
        document.getElementById("code").hidden = true; document.getElementById("follow").hidden = true; }
    }).then(function () { btn.disabled = false; btn.textContent = "🔒 Envoyer le signalement chiffré"; });
  });
  document.getElementById("again").addEventListener("click", function () { location.href = "/signaler/"; });
})();
