/* ===========================================================
   Archivo: static/js/reportes.js
   Función: Comportamiento del módulo de reportes.
            - Valida que la fecha inicial no sea mayor que la final.
   =========================================================== */

document.addEventListener("DOMContentLoaded", function () {

  document.querySelectorAll("form[data-validar-fechas]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const ini = form.querySelector("[name='fecha_inicio']");
      const fin = form.querySelector("[name='fecha_fin']");
      if (ini && fin && ini.value && fin.value && ini.value > fin.value) {
        e.preventDefault();
        alert("La fecha inicial no puede ser posterior a la final.");
      }
    });
  });
});
