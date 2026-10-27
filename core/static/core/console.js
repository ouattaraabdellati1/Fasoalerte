/* Console : confirmations et compteurs de caractères (pas de script dans le HTML, pour la CSP). */
(function () {
  "use strict";
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-confirm]");
    if (b && !confirm(b.getAttribute("data-confirm"))) e.preventDefault();
  });
  document.querySelectorAll("[data-count]").forEach(function (inp) {
    var max = Number(inp.getAttribute("data-count"));
    inp.setAttribute("maxlength", max);
    var c = document.querySelector('.counter[data-for="' + inp.id + '"]');
    function up() { if (c) c.textContent = inp.value.length + " / " + max; }
    inp.addEventListener("input", up); up();
  });
})();
