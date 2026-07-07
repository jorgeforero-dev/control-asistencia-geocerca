/* ===========================================================
   Archivo: static/js/trabajadores.js
   Función: Comportamiento del módulo de trabajadores.
            - Rellena el formulario de edición con los datos de la
              fila seleccionada (atributos data-*).
            - Muestra/oculta el panel de edición.
   =========================================================== */

document.addEventListener("DOMContentLoaded", function () {

  const panelEdicion = document.getElementById("panel-edicion");
  const formEdicion = document.getElementById("form-edicion");

  // Cada botón "Editar" lleva los datos del trabajador en data-*.
  document.querySelectorAll(".btn-editar").forEach(function (boton) {
    boton.addEventListener("click", function () {
      if (!formEdicion) return;

      // Construir la URL de envío del formulario con el id correcto.
      const id = boton.getAttribute("data-id");
      formEdicion.action = "/trabajadores/" + id + "/editar";

      // Volcar los datos en los campos del formulario.
      formEdicion.nombres.value   = boton.getAttribute("data-nombres") || "";
      formEdicion.apellidos.value = boton.getAttribute("data-apellidos") || "";
      formEdicion.cargo.value     = boton.getAttribute("data-cargo") || "";
      formEdicion.area.value      = boton.getAttribute("data-area") || "";
      formEdicion.turno.value     = boton.getAttribute("data-turno") || "";

      if (panelEdicion) {
        panelEdicion.classList.remove("oculto");
        panelEdicion.scrollIntoView({ behavior: "smooth" });
      }
    });
  });

  // Botón para cerrar el panel de edición.
  const cerrar = document.getElementById("cerrar-edicion");
  if (cerrar && panelEdicion) {
    cerrar.addEventListener("click", function () {
      panelEdicion.classList.add("oculto");
    });
  }
});
