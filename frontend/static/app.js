"use strict";

(() => {
  /* ============================================================
     Estado de la aplicación
     ============================================================ */
  const state = {
    carpetaLista: false,
    nombreArchivo: null,        // archivo activo
    archivos: [],
    analizando: false,
  };

  /* ============================================================
     Referencias al DOM
     ============================================================ */
  const $ = (id) => document.getElementById(id);

  const els = {
    dropzone: $("dropzone"),
    fileInput: $("file-input"),
    dzMain: $("dz-main"),
    dzSub: $("dz-sub"),
    dzFile: $("dz-file"),
    uploadBtn: $("upload-btn"),
    filesPanel: $("files-panel"),
    filesEmpty: $("files-empty"),
    fileSelect: $("file-select"),
    deleteBtn: $("delete-btn"),
    apiDot: $("api-status-dot"),
    apiStatus: $("api-status"),
    analysisPanel: $("analysis-panel"),
    emptyState: $("empty-state"),
    activeChip: $("active-file-chip"),
    promptInput: $("prompt-input"),
    analyzeBtn: $("analyze-btn"),
    results: $("results"),
    analysisBlock: $("analysis-text-block"),
    analysisText: $("analysis-text"),
    chartBlock: $("chart-block"),
    chartImg: $("chart-img"),
    codeBox: $("code-box"),
    codeContent: $("code-content"),
    codeFilename: $("code-filename"),
    downloadBtn: $("download-btn"),
    consoleError: $("console-error"),
    consoleErrorContent: $("console-error-content"),
    toasts: $("toasts"),
    tutorialModal: $("tutorial-modal"),
    tutorialOpen: $("tutorial-open"),
    tutorialClose: $("tutorial-close"),
    tutorialDone: $("tutorial-done"),
  };

  /* ============================================================
     Utilidades
     ============================================================ */
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function insertSpinner(btn, spinnerClass) {
    const s = document.createElement("span");
    s.className = "spinner" + (spinnerClass ? " " + spinnerClass : "");
    s.setAttribute("aria-hidden", "true");
    btn.prepend(s);
    return s;
  }

  function setBtnBusy(btn, busy, label) {
    btn.disabled = busy;
    const textNode = btn.querySelector("span");
    if (busy) {
      if (label) {
        btn.dataset.origLabel = textNode ? textNode.textContent : "";
        textNode.textContent = label;
      }
      insertSpinner(btn, btn.classList.contains("btn-primary") ? "on-accent" : "");
    } else {
      const sp = btn.querySelector(".spinner");
      if (sp) sp.remove();
      if (btn.dataset.origLabel) {
        textNode.textContent = btn.dataset.origLabel;
        delete btn.dataset.origLabel;
      }
    }
  }

  let toastCounter = 0;
  function toast(tipo, mensaje) {
    const iconos = {
      success: '<path d="M20 6 9 17l-5-5"/>',
      error: '<path d="M18 6 6 18M6 6l12 12"/>',
      warning: '<path d="M12 16v.01M12 8v5" /><path d="M12 3 2.5 20h19L12 3z"/>',
      info: '<path d="M12 11v5M12 8v.01" /><circle cx="12" cy="12" r="9"/>',
    };
    const node = document.createElement("div");
    node.className = "toast toast-" + tipo;
    node.setAttribute("role", "status");
    node.id = "toast-" + (++toastCounter);
    node.innerHTML =
      '<svg class="t-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      iconos[tipo] + "</svg>" +
      '<div class="t-msg" data-msg="' + toastCounter + '"></div>';
    node.querySelector("[data-msg]").textContent = mensaje;
    els.toasts.appendChild(node);
    setTimeout(() => {
      node.classList.add("leaving");
      setTimeout(() => node.remove(), 260);
    }, 4500);
  }

  /* ============================================================
     API (misma ruta de origen; nginx reenvía /api -> backend)
     ============================================================ */
  const API = "/api";

  async function pedir(resource, opciones) {
    const res = await fetch(API + resource, opciones);
    return res;
  }

  /* ============================================================
     Listar archivos
     ============================================================ */
  async function refrescarArchivos() {
    try {
      const res = await pedir("/files");
      if (res.status === 200) {
        const datos = await res.json();
        state.archivos = datos.archivos || [];
        state.carpetaLista = true;
        setConectado(true);
        volcarSelect();
        return;
      }
      setConectado(false);
      mostrarProblema("El servidor no devolvió la lista de archivos.");
    } catch (e) {
      setConectado(false);
    }
  }

  function setConectado(ok) {
    els.apiDot.classList.toggle("online", ok);
    els.apiDot.classList.toggle("offline", !ok);
    els.apiStatus.textContent = ok
      ? "Servidor conectado"
      : "No se pudo conectar con el backend";
    if (!ok) {
      els.fileSelect.disabled = true;
      els.deleteBtn.disabled = true;
    }
  }

  function volcarSelect() {
    const opt = state.archivos;
    els.filesEmpty.hidden = opt.length !== 0;
    els.filesPanel.hidden = opt.length === 0;

    // Si ya hay archivo activo y sigue en la lista, lo conservamos
    if (state.nombreArchivo) {
      const enLista = opt.includes(state.nombreArchivo);
      if (!enLista) state.nombreArchivo = null;
    }

    if (!state.nombreArchivo && opt.length > 0) {
      state.nombreArchivo = opt[0];
    }

    els.fileSelect.innerHTML = "";
    if (!opt.length) {
      const noop = document.createElement("option");
      noop.value = "";
      noop.textContent = "No hay archivos…";
      els.fileSelect.appendChild(noop);
      els.fileSelect.disabled = true;
      els.deleteBtn.disabled = true;
    } else {
      opt.forEach((f) => {
        const o = document.createElement("option");
        o.value = f;
        o.textContent = f;
        els.fileSelect.appendChild(o);
      });
      els.fileSelect.disabled = false;
      els.fileSelect.value = state.nombreArchivo;
      els.deleteBtn.disabled = false;
    }

    sincronizarUI();
  }

  /* ============================================================
     Sincronizar la UI según el archivo activo
     ============================================================ */
  function sincronizarUI() {
    if (state.nombreArchivo) {
      els.emptyState.hidden = true;
      els.analysisPanel.hidden = false;
      els.activeChip.textContent = state.nombreArchivo;
      els.activeChip.title = state.nombreArchivo;
    } else {
      els.emptyState.hidden = false;
      els.analysisPanel.hidden = true;
      if (!els.results.hidden) {
        // Si no hay archivo, ocultamos resultados pasados
        els.results.hidden = true;
        vaciarResultados();
      }
    }
  }

  function vaciarResultados() {
    els.analysisBlock.hidden = true;
    els.analysisText.innerHTML = "";
    els.chartBlock.hidden = true;
    els.chartImg.removeAttribute("src");
    els.codeBox.hidden = true;
    els.codeContent.textContent = "";
    els.consoleError.hidden = true;
    els.consoleErrorContent.textContent = "";
  }

  function mostrarProblema(msj) {
    toast("error", msj);
  }

  /* ============================================================
     Upload
     ============================================================ */
  async function subirArchivo(archivo) {
    if (!archivo) return;
    if (!archivo.name.toLowerCase().endsWith(".csv")) {
      toast("error", "Formato inválido. Solo se aceptan archivos .csv");
      return;
    }

    setBtnBusy(els.uploadBtn, true, "Subiendo…");
    try {
      const fd = new FormData();
      fd.append("file", archivo, archivo.name);
      const res = await pedir("/upload", { method: "POST", body: fd });

      if (res.status === 201) {
        state.nombreArchivo = archivo.name;
        toast("success", "Archivo guardado: " + archivo.name);
        await refrescarArchivos();
        siguienteCampoLimpio();
        desplazarHasta(els.filesPanel || els.analysisPanel, "center");
      } else {
        let detalle = "Error al subir el archivo.";
        try {
          const body = await res.json();
          if (body && body.detail) detalle = body.detail;
        } catch (e) { /* sin cuerpo */ }
        toast("error", detalle);
      }
    } catch (e) {
      toast("error", "Error de conexión: " + e.message);
    } finally {
      setBtnBusy(els.uploadBtn, false);
    }
  }

  function siguienteCampoLimpio() {
    els.fileInput.value = "";
    els.dropzone.classList.remove("has-file");
    els.dzFile.hidden = true;
  }

  function desplazarHasta(el, bloque) {
    if (!el) return;
    requestAnimationFrame(() => {
      el.scrollIntoView({ behavior: "smooth", block: bloque || "start" });
    });
  }

  /* ============================================================
     Eliminar archivo
     ============================================================ */
  async function eliminarArchivo() {
    const nombre = els.fileSelect.value;
    if (!nombre) return;

    if (!confirm(`¿Eliminar el archivo "${nombre}" del servidor?`)) return;

    setBtnBusy(els.deleteBtn, true, "Eliminando…");
    try {
      const res = await pedir(
        "/files/" + encodeURIComponent(nombre),
        { method: "DELETE" }
      );
      if (res.status === 200) {
        toast("success", "Archivo eliminado.");
        if (state.nombreArchivo === nombre) state.nombreArchivo = null;
        await refrescarArchivos();
      } else {
        toast("error", "No se pudo eliminar el archivo.");
      }
    } catch (e) {
      toast("error", "Error de conexión: " + e.message);
    } finally {
      setBtnBusy(els.deleteBtn, false);
    }
  }

  /* ============================================================
     Análisis
     ============================================================ */
  async function ejecutarAnalisis() {
    const prompt = els.promptInput.value;
    if (!prompt.trim()) {
      toast("warning", "Por favor, escribe una instrucción.");
      els.promptInput.focus();
      return;
    }
    if (!state.nombreArchivo) {
      toast("warning", "Primero selecciona un dataset para analizar.");
      return;
    }
    if (state.analizando) return;

    state.analizando = true;
    setBtnBusy(els.analyzeBtn, true, "Generando y ejecutando código…");
    vaciarResultados();
    els.results.hidden = false;
    // Esqueleto de carga
    els.analysisBlock.hidden = false;
    els.analysisText.innerHTML =
      '<p style="color:var(--text-faint)">Generando análisis… esto puede tomar unos segundos.</p>';

    try {
      const res = await pedir("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          nombre_archivo: state.nombreArchivo,
          prompt_usuario: prompt,
        }),
      });

      if (res.status === 200) {
        const datos = await res.json();
        pintarResultados(datos);
      } else {
        let detalle = "Error del servidor: " + res.status;
        try {
          const body = await res.json();
          if (body && body.detail) detalle = "Error del servidor: " + body.detail;
        } catch (e) { /* sin cuerpo */ }
        toast("error", detalle);
        els.results.hidden = true;
      }
    } catch (e) {
      toast("error", "Error de conexión con el servidor: " + e.message);
      els.results.hidden = true;
    } finally {
      state.analizando = false;
      setBtnBusy(els.analyzeBtn, false);
    }
  }

  function pintarResultados(datos) {
    // 1. Texto del análisis
    const texto = datos.analisis_texto || "No se generó texto descriptivo.";
    els.analysisText.innerHTML = renderLongform(texto);
    els.analysisBlock.hidden = false;
    reanimar(els.analysisBlock);

    // 2. Gráfico
    if (datos.imagen_base64) {
      els.chartImg.src = "data:image/png;base64," + datos.imagen_base64;
      els.chartBlock.hidden = false;
      reanimar(els.chartBlock);
    }

    // 3. Código + consola
    els.consoleError.hidden = true;
    let visibles = 0;
    const codigo = datos.codigo_generado || "";
    if (codigo) {
      els.codeFilename.textContent = "script_analisis.py";
      pintarCodigo(codigo);
      els.codeBox.hidden = false;
      visibles++;
    }
    if (datos.consola_errores) {
      els.consoleErrorContent.textContent = datos.consola_errores;
      els.consoleError.hidden = false;
      visibles++;
    }
    if (visibles) reanimar(els.codeBox);

    els.chartImg.onload = () => reanimar(els.chartBlock);
  }

  function reanimar(el) {
    el.classList.remove("reveal");
    void el.offsetWidth; // reinicia la animación
    el.classList.add("reveal");
  }

  /* ============================================================
     Tutorial
     ============================================================ */
  const TUTORIAL_FLAG = "tutorial_visto";

  function abrirTutorial() {
    els.tutorialModal.hidden = false;
    document.body.style.overflow = "hidden";
    els.tutorialClose.focus();
  }

  function cerrarTutorial() {
    els.tutorialModal.hidden = true;
    document.body.style.overflow = "";
    els.tutorialOpen.focus();
  }

  /* Renderiza markdown simple: párrafos, títulos, listas, negritas, código */
  function renderLongform(md) {
    const parrafos = String(md).split(/\n{2,}/);
    return parrafos
      .map((bloque) => {
        const t = bloque.trim();
        if (!t) return "";
        if (/^#{1,3}\s/.test(t)) {
          const nivel = t.match(/^#{1,3}/)[0].length;
          const tag = "h" + (nivel + 1);
          return "<" + tag + ">" + inline(t.replace(/^#{1,3}\s*/, "")) + "</" + tag + ">";
        }
        if (/^\s*[-*]\s/.test(t) || /^\s*\d+\.\s/.test(t)) {
          const items = t.split(/\n(?=\s*[-*]?\s|\s*\d+\.\s)/);
          const lista = items
            .filter((i) => /^\s*[-*]\s/.test(i) || /^\s*\d+\.\s/.test(i))
            .map((i) => "<li>" + inline(i.replace(/^\s*[-*]\s+|^\s*\d+\.\s+/, "")) + "</li>")
            .join("");
          return "<ul>" + lista + "</ul>";
        }
        return "<p>" + inline(t) + "</p>";
      })
      .join("");
  }

  function inline(texto) {
    let out = esc(texto)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^\*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^\*]+)\*/g, "<em>$1</em>");
    return out;
  }

  /* Resaltado ligero de Python en el bloque de código */
  function pintarCodigo(codigo) {
    const kw = "\\b(?:import|from|def|return|if|elif|else|for|while|in|not|and|or|print|plt|df|pd|ax|True|False|None)\\b";
    let html = esc(codigo);
    html = html.replace(/(#.*)$/gm, "<span class=hl-str>$1</span>");
    html = html.replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, "<span class=hl-str>$&</span>");
    html = html.replace(kw, "<span class=hl-kw>$&</span>");
    els.codeContent.innerHTML = html;

    // Descarga del script
    els.downloadBtn.onclick = () => {
      const blob = new Blob([codigo], { type: "text/x-python" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "script_analisis.py";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 500);
    };
  }

  /* ============================================================
     Eventos
     ============================================================ */
  function initEventos() {
    // Selección de archivo local
    els.fileInput.addEventListener("change", () => {
      if (els.fileInput.files.length) {
        const f = els.fileInput.files[0];
        els.dropzone.classList.add("has-file");
        els.dzFile.hidden = false;
        els.dzFile.textContent = "✓ " + f.name;
      } else {
        els.dropzone.classList.remove("has-file");
        els.dzFile.hidden = true;
      }
    });

    // Arrastrar y soltar
    ["dragenter", "dragover"].forEach((ev) =>
      els.dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        els.dropzone.classList.add("dragover");
      })
    );
    ["dragleave", "drop"].forEach((ev) =>
      els.dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        els.dropzone.classList.remove("dragover");
      })
    );
    els.dropzone.addEventListener("drop", (e) => {
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) {
        const dt = new DataTransfer();
        dt.items.add(f);
        els.fileInput.files = dt.files;
        els.fileInput.dispatchEvent(new Event("change"));
      }
    });

    els.uploadBtn.addEventListener("click", () => {
      if (els.fileInput.files.length) {
        subirArchivo(els.fileInput.files[0]);
      } else {
        toast("warning", "Selecciona primero un archivo CSV.");
      }
    });

    // Cambio de dataset activo
    els.fileSelect.addEventListener("change", () => {
      state.nombreArchivo = els.fileSelect.value;
      sincronizarUI();
    });

    els.deleteBtn.addEventListener("click", eliminarArchivo);

    els.analyzeBtn.addEventListener("click", ejecutarAnalisis);

    els.promptInput.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        ejecutarAnalisis();
      }
    });

    els.tutorialOpen.addEventListener("click", abrirTutorial);
    els.tutorialClose.addEventListener("click", cerrarTutorial);
    els.tutorialDone.addEventListener("click", cerrarTutorial);
    els.tutorialModal.addEventListener("click", (e) => {
      if (e.target === els.tutorialModal) cerrarTutorial();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !els.tutorialModal.hidden) cerrarTutorial();
    });
  }

  /* ============================================================
     Arranque
     ============================================================ */
  async function init() {
    initEventos();
    // Tutorial: se muestra una sola vez en la primera visita
    if (!localStorage.getItem(TUTORIAL_FLAG)) {
      localStorage.setItem(TUTORIAL_FLAG, "1");
      abrirTutorial();
    }
    await refrescarArchivos();
    sincronizarUI();
    // Reintento periódico mientras el backend no responda
    if (!state.carpetaLista) {
      setTimeout(async () => {
        await refrescarArchivos();
        sincronizarUI();
      }, 8000);
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();