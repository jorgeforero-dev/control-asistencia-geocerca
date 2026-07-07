/* ===========================================================
   Archivo: static/js/asistencia.js
   Función: Comportamiento de la pantalla de marcaje.
            - Reloj en vivo.
            - Buscador rápido de trabajadores en el selector/tabla.
   =========================================================== */

document.addEventListener("DOMContentLoaded", function () {

  // 1) Reloj en vivo en el elemento #reloj (si existe en la página).
  const reloj = document.getElementById("reloj");
  if (reloj) {
    const actualizar = function () {
      const ahora = new Date();
      reloj.textContent = ahora.toLocaleTimeString("es-CO");
    };
    actualizar();
    setInterval(actualizar, 1000);
  }

  // 2) Buscador: filtra las filas de la tabla por documento o nombre.
  const buscador = document.getElementById("buscador");
  if (buscador) {
    buscador.addEventListener("input", function () {
      const texto = this.value.toLowerCase();
      document.querySelectorAll("#tabla-registros tbody tr").forEach(function (fila) {
        fila.style.display = fila.textContent.toLowerCase().includes(texto) ? "" : "none";
      });
    });
  }
});
