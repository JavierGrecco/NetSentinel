/* Preferencia de apariencia compartida por todas las páginas de NetSentinel. */
(() => {
  "use strict";
  const STORAGE_KEY = "netsentinel-theme";
  const THEMES = new Set(["dark", "medium", "light"]);
  const DEFAULT_THEME = "dark";

  function readTheme() {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      return THEMES.has(saved) ? saved : DEFAULT_THEME;
    } catch (_) {
      return DEFAULT_THEME;
    }
  }

  function applyTheme(theme, persist) {
    const selected = THEMES.has(theme) ? theme : DEFAULT_THEME;
    document.documentElement.dataset.theme = selected;
    document.documentElement.style.colorScheme = selected === "dark" ? "dark" : "light";
    const selector = document.getElementById("themeSelect");
    if (selector && selector.value !== selected) selector.value = selected;
    if (persist) {
      try {
        window.localStorage.setItem(STORAGE_KEY, selected);
      } catch (_) {
        // La apariencia sigue aplicada en esta página si el navegador bloquea el almacenamiento local.
      }
    }
  }

  // Aplica la preferencia antes de que termine de renderizar la página para evitar un salto de tema.
  applyTheme(readTheme(), false);

  document.addEventListener("DOMContentLoaded", () => {
    const selector = document.getElementById("themeSelect");
    if (selector) {
      selector.value = readTheme();
      selector.addEventListener("change", () => applyTheme(selector.value, true));
    }
  });

  window.addEventListener("storage", event => {
    if (event.key === STORAGE_KEY) applyTheme(event.newValue, false);
  });
})();