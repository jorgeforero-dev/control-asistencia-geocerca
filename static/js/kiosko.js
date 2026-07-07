/* ===========================================================
   Archivo: static/js/kiosko.js
   Función: Lógica de la pantalla pública de marcación (kiosko).
            - Enciende la cámara y muestra el video en vivo.
            - Obtiene la ubicación (GPS) del dispositivo.
            - Al presionar "Marcar", captura la foto AUTOMÁTICAMENTE
              en ese instante y la envía junto al documento y las
              coordenadas. Ya no hay botón separado de "Tomar foto".
   Requisitos: cámara y ubicación necesitan HTTPS en producción
               (en localhost funcionan para pruebas).
   =========================================================== */

document.addEventListener("DOMContentLoaded", function () {

  // ---- Leer configuración desde los atributos data-* ----
  const cfgEl = document.getElementById("kiosko-config");
  const CONFIG = {
    exigirFoto: cfgEl.dataset.exigirFoto === "1",
    validarUbicacion: cfgEl.dataset.validarUbicacion === "1",
    urlMarcar: cfgEl.dataset.urlMarcar,
  };

  // ---- Referencias a los elementos de la página ----
  const video = document.getElementById("video");
  const lienzo = document.getElementById("lienzo");
  const btnMarcar = document.getElementById("btn-marcar");
  const inputDoc = document.getElementById("documento");
  const resultado = document.getElementById("resultado");
  const ubicTxt = document.getElementById("ubic-txt");
  const reloj = document.getElementById("reloj");

  // ---- Variables de estado ----
  let camaraLista = false;            // ¿la cámara ya da imagen?
  let coords = { lat: null, lon: null };

  // ---- Reloj en vivo ----
  function actualizarReloj() {
    reloj.textContent = new Date().toLocaleTimeString("es-CO");
  }
  actualizarReloj();
  setInterval(actualizarReloj, 1000);

  // ---- 1) Encender la cámara ----
  function iniciarCamara() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      mostrar("Este navegador no permite usar la cámara.", false);
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false })
      .then(function (stream) {
        video.srcObject = stream;
        // Marcar la cámara como lista cuando empiece a dar imagen
        video.addEventListener("playing", function () {
          camaraLista = true;
          revisarListo();
        });
      })
      .catch(function () {
        mostrar("No se pudo acceder a la cámara. Active los permisos.", false);
      });
  }

  // ---- 2) Obtener la ubicación ----
  function iniciarUbicacion() {
    if (!CONFIG.validarUbicacion) {
      ubicTxt.textContent = "no requerida";
      return;
    }
    if (!navigator.geolocation) {
      ubicTxt.textContent = "no disponible en este equipo";
      return;
    }
    ubicTxt.textContent = "obteniendo…";
    // watchPosition refresca la ubicación si el trabajador se mueve.
    navigator.geolocation.watchPosition(
      function (pos) {
        coords.lat = pos.coords.latitude;
        coords.lon = pos.coords.longitude;
        ubicTxt.textContent = "lista ✓";
        revisarListo();
      },
      function () {
        ubicTxt.textContent = "permiso denegado";
      },
      { enableHighAccuracy: true, maximumAge: 10000, timeout: 15000 }
    );
  }

  // ---- Capturar la foto del momento (devuelve data URL o null) ----
  function capturarFoto() {
    if (!video.videoWidth) {
      return null;  // la cámara aún no da imagen
    }
    lienzo.width = video.videoWidth;
    lienzo.height = video.videoHeight;
    lienzo.getContext("2d").drawImage(video, 0, 0);
    // Imagen JPG comprimida (calidad 0.7)
    return lienzo.toDataURL("image/jpeg", 0.7);
  }

  // ---- Habilitar el botón Marcar solo cuando todo esté listo ----
  function revisarListo() {
    const docOk = inputDoc.value.trim().length > 0;
    const fotoOk = !CONFIG.exigirFoto || camaraLista;
    const ubicOk = !CONFIG.validarUbicacion || coords.lat !== null;
    btnMarcar.disabled = !(docOk && fotoOk && ubicOk);
  }
  inputDoc.addEventListener("input", revisarListo);

  // ---- Enviar el marcaje (captura la foto en este instante) ----
  btnMarcar.addEventListener("click", function () {
    // Capturar la foto justo ahora, automáticamente
    let foto = null;
    if (CONFIG.exigirFoto) {
      foto = capturarFoto();
      if (!foto) {
        mostrar("La cámara aún no está lista. Espere un momento.", false);
        return;
      }
    }

    btnMarcar.disabled = true;
    btnMarcar.textContent = "Marcando…";

    fetch(CONFIG.urlMarcar, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        documento: inputDoc.value.trim(),
        foto: foto,
        lat: coords.lat,
        lon: coords.lon,
      }),
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
      .then(function (res) {
        if (res.ok && res.d.ok) {
          mostrar(res.d.trabajador + " — " + res.d.mensaje, true);
          reiniciar();
        } else {
          mostrar(res.d.mensaje || "No se pudo marcar.", false);
          btnMarcar.textContent = "Marcar";
          revisarListo();
        }
      })
      .catch(function () {
        mostrar("Error de conexión. Intente de nuevo.", false);
        btnMarcar.textContent = "Marcar";
        revisarListo();
      });
  });

  // ---- Mostrar mensaje de resultado ----
  function mostrar(texto, exito) {
    resultado.textContent = texto;
    resultado.classList.remove("oculto", "ok", "error");
    resultado.classList.add(exito ? "ok" : "error");
  }

  // ---- Reiniciar la pantalla tras un marcaje exitoso ----
  function reiniciar() {
    setTimeout(function () {
      inputDoc.value = "";
      btnMarcar.textContent = "Marcar";
      btnMarcar.disabled = true;
      resultado.classList.add("oculto");
    }, 4000);
  }

  // ---- Arranque ----
  iniciarCamara();
  iniciarUbicacion();
});
