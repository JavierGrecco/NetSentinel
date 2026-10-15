/* Navegación por sectores para pantallas con mucha información. */
(() => {
  "use strict";
  const tabs = Array.from(document.querySelectorAll("[data-tab-target]"));
  const panels = Array.from(document.querySelectorAll("[data-tab-panel]"));
  if (!tabs.length || !panels.length) return;

  function hashFor(tab) {
    return tab.dataset.tabHash || tab.dataset.tabTarget;
  }

  function activate(tab, updateAddress = false) {
    const target = tab.dataset.tabTarget;
    if (!panels.some(panel => panel.id === target)) return;
    for (const candidate of tabs) {
      const selected = candidate === tab;
      candidate.setAttribute("aria-selected", String(selected));
      candidate.tabIndex = selected ? 0 : -1;
    }
    for (const panel of panels) {
      panel.hidden = panel.id !== target;
    }
    if (updateAddress && window.history && window.history.replaceState) {
      const hash = hashFor(tab);
      window.history.replaceState(null, "", window.location.pathname + window.location.search + "#" + encodeURIComponent(hash));
    }
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => activate(tab, true));
    tab.addEventListener("keydown", event => {
      let nextIndex = index;
      if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") nextIndex = 0;
      else if (event.key === "End") nextIndex = tabs.length - 1;
      else return;
      event.preventDefault();
      tabs[nextIndex].focus();
      activate(tabs[nextIndex], true);
    });
  });

  const currentHash = decodeURIComponent(window.location.hash.replace(/^#/, ""));
  const initial = tabs.find(tab => hashFor(tab) === currentHash || tab.dataset.tabTarget === currentHash)
    || tabs.find(tab => tab.getAttribute("aria-selected") === "true")
    || tabs[0];
  activate(initial);
})();