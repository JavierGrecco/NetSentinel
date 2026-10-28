"""Regression tests for the guided acceptance wizard's iterative UX contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "src/netsentinel/static/guided-test.html"
JS_PATH = ROOT / "src/netsentinel/static/guided-test.js"
CSS_PATH = ROOT / "src/netsentinel/static/guided-test.css"
GUIDE_PATH = ROOT / "docs/EXPERT_ACCEPTANCE_LAB.md"


def test_progress_is_local_and_resumed_sessions_are_explained():
    html = HTML_PATH.read_text(encoding="utf-8")
    script = JS_PATH.read_text(encoding="utf-8")

    assert 'id="wizardSaveStatus"' in html
    assert 'aria-live="polite"' in html[html.index('id="wizardSaveStatus"') - 50:html.index('id="wizardSaveStatus"') + 100]
    assert 'id="wizardResumeNotice"' in html
    assert "Guardado en este navegador" in script
    assert "Se recuperó un recorrido anterior de este navegador" in script
    assert "window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))" in script
    assert "checking: false" in script
    assert "Number.isFinite(Date.parse(saved.finishedAt))" in script


def test_summary_allows_direct_review_without_restarting_the_wizard():
    html = HTML_PATH.read_text(encoding="utf-8")
    script = JS_PATH.read_text(encoding="utf-8")

    assert 'id="wizardReviewNextIssue"' in html
    assert 'id="wizardSummaryRows"' in html
    assert "reviewButton.dataset.wizardReviewStep = step.id" in script
    assert 'addEventListener("click", (event) => {' in script
    assert "function jumpToStep(stepId)" in script
    assert "state.finishedAt = null" in script
    assert "Las respuestas y notas anteriores se conservaron" in script
    assert 'id="wizardReturnToSummary"' in html
    assert 'state.returnToSummary = returningFromCompletedSummary' in script
    assert 'addEventListener("click", () => {' in script
    assert "Resumen actualizado con los resultados y notas conservados" in script
    assert "function reopenedLinkLabel(label)" in script
    assert 'record.opened ? reopenedLinkLabel(baseLinkLabel) : baseLinkLabel' in script
    assert "Después pulsá «Comprobar ahora»." in script
    assert "no hace falta cerrar la otra" in script


def test_manual_acceptance_does_not_require_closing_the_module_tab_before_checking():
    script = JS_PATH.read_text(encoding="utf-8")

    assert "if (step.checkKey) return Boolean(record.autoChecked);" in script
    assert 'record.autoResult.status === "needs_action"' in script
    assert 'Boolean(step.checkAfterAction && !record.opened)' not in script
    assert 'link: "/activity#importar"' in script
    assert "⌘⇧G" in script
    assert "No hace falta cerrar la otra" in script


def test_wizard_reuses_one_module_tab_instead_of_opening_a_new_tab_for_every_step():
    html = HTML_PATH.read_text(encoding="utf-8")

    assert 'id="wizardActionLink"' in html
    assert 'target="netsentinel-acceptance-module"' in html
    assert 'target="_blank"' not in html


def test_empty_activity_and_map_states_are_reported_as_missing_actions_not_product_failures():
    script = JS_PATH.read_text(encoding="utf-8")

    assert "Todavía no hay eventos del CSV guardados. Esto no demuestra un fallo del importador" in script
    assert "Todavía no hay CSV válido importado" in script
    assert "Todavía no se encontró ningún registro Zeek de la prueba" in script
    assert "Todavía no hay eventos para mostrar; importá activity.csv" in script
    assert 'ok: cityStatus === "available", level: cityStatus === "available" ? undefined : "warning"' in script


def test_rechecking_a_manual_step_revokes_a_stale_pass_when_the_check_fails():
    script = JS_PATH.read_text(encoding="utf-8")

    assert 'else if (!result.ok && record.outcome === "passed")' in script
    assert "record.outcome = null;" in script
    assert "record.resultTimestamp = null;" in script


def test_phase_navigation_does_not_unlock_future_work_prematurely():
    script = JS_PATH.read_text(encoding="utf-8")
    html = HTML_PATH.read_text(encoding="utf-8")
    css = CSS_PATH.read_text(encoding="utf-8")

    assert 'const phaseNames = ["Preparación", "Red", "Actividad", "Geolocalización", "Hallazgos", "Forense", "Cierre"]' in script
    assert "const prerequisitesMet = trackedSteps.slice(0, firstIndex)" in script
    assert "button.disabled = !prerequisitesMet && !active" in script
    assert ".wizard-milestone-button:focus-visible" in css
    assert 'aria-label="Fases de la prueba"' in html


def test_progress_distinguishes_passed_failed_blocked_and_pending_steps():
    script = JS_PATH.read_text(encoding="utf-8")
    assert "correctos" in script
    assert "fallidos" in script
    assert "sin comprobar" in script
    assert "pendientes" in script
    assert 'setAttribute("aria-valuetext", detail)' in script


def test_correlation_step_is_in_the_wizard_and_keeps_legacy_progress():
    script = JS_PATH.read_text(encoding="utf-8")
    html = HTML_PATH.read_text(encoding="utf-8")

    assert 'id: "findings-correlation"' in script
    assert 'checkKey: "findings-correlation"' in script
    assert "async function checkFindingsCorrelation()" in script
    assert '"zeek:CManualScenario101"' in script
    assert '"zeek:CManualScenario102"' in script
    assert '"/api/findings?state=all&limit=200"' in script
    assert "format_version: 4" in script
    assert "LEGACY_STEP_IDS" in script
    assert 'aria-valuetext="0 de 13 pasos con resultado"' in html


def test_acceptance_guide_documents_iteration_and_local_resume():
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    assert "13 pasos evaluables" in guide
    assert "Hallazgos y correlación" in guide
    assert "un indicador visible" in guide
    assert "cada fila tiene una acción para revisar directamente ese paso" in guide
