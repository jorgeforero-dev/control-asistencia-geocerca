/* ===========================================================
   Archivo: static/js/main.js
   Función: Utilidades de interfaz comunes a todas las páginas.
            - Resaltar el enlace activo del menú.
            - Cerrar alertas automáticamente.
            - Confirmar acciones peligrosas (data-confirmar).
   No contiene lógica de negocio: solo comportamiento de UI.
   =========================================================== */

document.addEventListener("DOMContentLoaded", function () {

  // 1) Resaltar en el menú el enlace de la página actual.
  const rutaActual = window.location.pathname;
  document.querySelectorAll(".nav__links a").forEach(function (enlace) {
    if (enlace.getAttribute("href") === rutaActual) {
      enlace.classList.add("activo");
    }
  });

  // 2) Ocultar mensajes flash después de 5 segundos.
  document.querySelectorAll(".alerta").forEach(function (alerta) {
    setTimeout(function () { alerta.style.display = "none"; }, 5000);
  });

  // 3) Pedir confirmación en formularios marcados con data-confirmar.
  document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      const mensaje = form.getAttribute("data-confirmar") || "¿Confirma la acción?";
      if (!window.confirm(mensaje)) { e.preventDefault(); }
    });
  });
});
