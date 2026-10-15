/* Preferencia de apariencia compartida por todas las páginas de NetSentinel. */
(() => {
  "use strict";
  const STORAGE_KEY = "netsentinel-theme";
  const THEMES = new Set(["dark", "medium", "light"]);
  const DEFAULT_THEME = "dark";
  const CONTROL_NAME = "themeSelect";

  function readTheme() {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      return THEMES.has(saved) ? saved : DEFAULT_THEME;
    } catch (_) {
      return DEFAULT_THEME;
    }
  }

  function syncThemeControls(theme) {
    const controls = document.querySelectorAll(`input[name="${CONTROL_NAME}"]`);
    controls.forEach(control => {
      control.checked = control.value === theme;
    });
  }

  function applyTheme(theme, persist) {
    const selected = THEMES.has(theme) ? theme : DEFAULT_THEME;
    document.documentElement.dataset.theme = selected;
    document.documentElement.style.colorScheme = selected === "dark" ? "dark" : "light";
    syncThemeControls(selected);

    if (persist) {
      try {
        window.localStorage.setItem(STORAGE_KEY, selected);
      } catch (_) {
        // La apariencia sigue aplicada en esta página si el navegador bloquea el almacenamiento local.
      }
    }
  }

  // Aplica la preferencia antes del primer render para evitar un salto de tema.
  applyTheme(readTheme(), false);

  document.addEventListener("DOMContentLoaded", () => {
    syncThemeControls(readTheme());
    const controls = document.querySelectorAll(`input[name="${CONTROL_NAME}"]`);
    controls.forEach(control => {
      control.addEventListener("change", () => {
        if (control.checked) applyTheme(control.value, true);
      });
    });
  });

  // Si se cambia la apariencia en otra pestaña, esta ventana también se actualiza.
  window.addEventListener("storage", event => {
    if (event.key === STORAGE_KEY) applyTheme(event.newValue, false);
  });
})();
