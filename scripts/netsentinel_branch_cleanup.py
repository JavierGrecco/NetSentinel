#!/usr/bin/env python3
"""Limpieza remota auditada de ramas NetSentinel (manifiesto issue #221)."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = "JavierGrecco/NetSentinel"
ISSUE = 221
EXPECTED = 190
CONFIRM_TOKEN = "BORRAR-RAMAS-NETSENTINEL"
TEMP_BRANCHES = {
    "ops/one-time-branch-cleanup-2026-11",
    "ops/cleanup-command-trigger-2026-11",
    "fix/cleanup-temp-branch-validation-2026-11",
}
PROTECTED = {
    "main",
    "feat/findings-zeek-evidence-context-2026-10-23",  # PR #200
    "fix/activity-blocked-provenance-2026-11",          # PR #222
}
MANIFEST_HEADING = "## Manifiesto de referencias y SHA esperados — corte"
A2_HEADING = "### A2. Cuatro pares de punteros redundantes"
ROW_RE = re.compile(
    r"^\|\s*\x60([^\x60]+)\x60\s*\|\s*\x60([0-9a-f]{40})\x60\s*\|\s*(A1|A2|B)\s*"
    r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$"
)
A2_RE = re.compile(r"^\|\s*\x60([^\x60]+)\x60\s*/\s*\x60([^\x60]+)\x60\s*\|")


class CleanupError(RuntimeError):
    pass


def run(argv: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(argv, cwd=str(cwd) if cwd else None, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if check and p.returncode:
        raise CleanupError(p.stderr.strip() or p.stdout.strip() or f"exit {p.returncode}: {argv!r}")
    return p


def gh_json(endpoint: str, *, paginate: bool = False):
    args = ["gh", "api"]
    if paginate:
        args += ["--paginate", "--slurp"]
    args.append(endpoint)
    try:
        value = json.loads(run(args).stdout)
    except json.JSONDecodeError as exc:
        raise CleanupError(f"Respuesta JSON inválida de GitHub: {endpoint}") from exc
    if not paginate:
        return value
    if not isinstance(value, list):
        raise CleanupError(f"Respuesta paginada inesperada: {endpoint}")
    return [x for page in value for x in page] if value and all(isinstance(x, list) for x in value) else value


def repo_root() -> Path:
    root = Path(run(["git", "rev-parse", "--show-toplevel"]).stdout.strip()).resolve()
    remote = run(["git", "remote", "get-url", "origin"], cwd=root).stdout.strip().lower().removesuffix(".git")
    if "github.com/javiergrecco/netsentinel" not in remote and "javiergrecco:netsentinel" not in remote:
        raise CleanupError(f"El origin no corresponde a {REPO}: {remote!r}")
    return root


def parse_manifest(body: str):
    if MANIFEST_HEADING not in body or A2_HEADING not in body:
        raise CleanupError("El issue #221 no contiene el manifiesto vigente y la sección A2.")
    rows = {}
    for line in body.split(MANIFEST_HEADING, 1)[1].splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            if rows and line.startswith("## "):
                break
            continue
        branch, sha, cls, pr_text, merge_text = m.groups()
        pr_text, merge_text = pr_text.strip(), merge_text.strip().strip(chr(96))
        if branch in rows:
            raise CleanupError(f"Rama duplicada en manifiesto: {branch}")
        rows[branch] = {
            "branch": branch, "sha": sha, "class": cls,
            "pr": int(pr_text) if pr_text.isdigit() else None,
            "merge_prefix": merge_text if re.fullmatch(r"[0-9a-f]{7,40}", merge_text) else None,
        }
    if len(rows) != EXPECTED:
        raise CleanupError(f"El manifiesto debería tener {EXPECTED} ramas; contiene {len(rows)}.")
    a2_text = body.split(A2_HEADING, 1)[1].split("## Lote B", 1)[0]
    pairs = [m.groups() for line in a2_text.splitlines() if (m := A2_RE.match(line.strip()))]
    if len(pairs) != 4:
        raise CleanupError(f"Se esperaban 4 pares A2; se encontraron {len(pairs)}.")
    for left, right in pairs:
        if left not in rows or right not in rows:
            raise CleanupError(f"Par A2 incompleto: {left} / {right}")
    a1 = [x for x in rows.values() if x["class"] == "A1"]
    a2 = [x for x in rows.values() if x["class"] == "A2"]
    b = [x for x in rows.values() if x["class"] == "B"]
    if len(a1) != 163 or len(a2) != 4 or len(b) != 23:
        raise CleanupError(f"Clases inesperadas en manifiesto: A1={len(a1)}, A2={len(a2)}, B={len(b)}.")
    if any(not x["pr"] or not x["merge_prefix"] for x in a1):
        raise CleanupError("Las 163 filas A1 deben incluir PR y prefijo de merge válidos.")
    return rows, pairs


def verify(root: Path):
    if not shutil.which("gh") or not shutil.which("git"):
        raise CleanupError("Faltan git o GitHub CLI; el workflow debe ejecutarse en GitHub Actions.")
    run(["gh", "auth", "status"])
    repo = gh_json(f"repos/{REPO}")
    if repo.get("default_branch") != "main":
        raise CleanupError(f"La rama predeterminada no es main: {repo.get('default_branch')!r}")
    issue = gh_json(f"repos/{REPO}/issues/{ISSUE}")
    if issue.get("state") != "open":
        raise CleanupError(f"El issue #{ISSUE} no está abierto.")
    rows, pairs = parse_manifest(issue.get("body", ""))

    branches = gh_json(f"repos/{REPO}/branches?per_page=100", paginate=True)
    remote = {b["name"]: b["commit"]["sha"] for b in branches if b.get("name") and b.get("commit", {}).get("sha")}
    candidates = set(rows)
    unexpected = set(remote) - candidates - PROTECTED - TEMP_BRANCHES
    if unexpected:
        raise CleanupError("Hay ramas no auditadas; se detiene sin borrar: " + ", ".join(sorted(unexpected)))
    if "main" not in remote:
        raise CleanupError("No se encontró main en el inventario.")
    protected_present = PROTECTED & set(remote)

    open_prs = gh_json(f"repos/{REPO}/pulls?state=open&per_page=100", paginate=True)
    open_refs = set()
    for pr in open_prs:
        for side in ("head", "base"):
            ref = (pr.get(side) or {}).get("ref")
            if ref:
                open_refs.add(ref)
    collisions = candidates & open_refs
    if collisions:
        raise CleanupError("Hay candidatas asociadas a PR abiertas: " + ", ".join(sorted(collisions)))

    closed_prs = gh_json(f"repos/{REPO}/pulls?state=closed&per_page=100", paginate=True)
    by_number = {int(p["number"]): p for p in closed_prs if p.get("number") is not None}
    for item in rows.values():
        if item["class"] != "A1":
            continue
        pr = by_number.get(item["pr"])
        head = (pr or {}).get("head") or {}
        if not pr or not pr.get("merged_at"):
            raise CleanupError(f"La PR #{item['pr']} no figura como fusionada.")
        if head.get("ref") != item["branch"] or head.get("sha") != item["sha"]:
            raise CleanupError(f"La PR #{item['pr']} ya no coincide con {item['branch']} y su SHA.")
        merge_sha = pr.get("merge_commit_sha") or ""
        if not merge_sha.startswith(item["merge_prefix"] or "!"):
            raise CleanupError(f"El merge SHA de la PR #{item['pr']} cambió.")
        item["merge_sha"] = merge_sha

    for left, right in pairs:
        lsha, rsha = remote.get(left), remote.get(right)
        if lsha and lsha != rows[left]["sha"]:
            raise CleanupError(f"Cambió el SHA auditado de {left}.")
        if rsha and rsha != rows[right]["sha"]:
            raise CleanupError(f"Cambió el SHA auditado de {right}.")
        if lsha and rsha and lsha != rsha:
            raise CleanupError(f"El par A2 {left} / {right} ya no comparte SHA.")

    remaining, absent = [], []
    for name, item in sorted(rows.items()):
        sha = remote.get(name)
        if sha is None:
            absent.append(name)
        elif sha != item["sha"]:
            raise CleanupError(f"El SHA de {name} cambió: {sha} != {item['sha']}.")
        else:
            remaining.append(item)

    shallow = run(["git", "rev-parse", "--is-shallow-repository"], cwd=root).stdout.strip()
    if shallow == "true":
        run(["git", "fetch", "--unshallow", "origin", "main"], cwd=root)
    else:
        run(["git", "fetch", "origin", "main"], cwd=root)
    local_main = run(["git", "rev-parse", "refs/remotes/origin/main"], cwd=root).stdout.strip()
    if local_main != remote["main"]:
        raise CleanupError("El main del runner no coincide con el HEAD remoto; se detiene.")
    history = set(run(["git", "rev-list", "refs/remotes/origin/main"], cwd=root).stdout.splitlines())
    for item in rows.values():
        if item["class"] == "A1" and item["merge_sha"] not in history:
            raise CleanupError(f"El merge de la PR #{item['pr']} no está en main.")

    temp_refs = {name: remote[name] for name in TEMP_BRANCHES if name in remote}
    for name, sha in temp_refs.items():
        merged = [
            pr for pr in closed_prs
            if pr.get("merged_at")
            and (pr.get("head") or {}).get("ref") == name
            and (pr.get("head") or {}).get("sha") == sha
        ]
        if len(merged) != 1:
            raise CleanupError(f"La rama temporal {name} no tiene una única PR fusionada con el mismo HEAD.")
        merge_sha = merged[0].get("merge_commit_sha")
        if not merge_sha or merge_sha not in history:
            raise CleanupError(f"El merge de la PR temporal de {name} no está en main.")
    return remaining, absent, remote["main"], protected_present, temp_refs


def delete_ref(root: Path, branch: str, sha: str):
    lease = f"--force-with-lease=refs/heads/{branch}:{sha}"
    run(["git", "push", "--porcelain", lease, "origin", f":refs/heads/{branch}"], cwd=root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Borrado auditado de ramas remotas NetSentinel.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="Solo valida y lista; modo predeterminado.")
    group.add_argument("--execute", action="store_true", help="Borra únicamente tras doble confirmación.")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--yes", action="store_true", help="Modo no interactivo para GitHub Actions.")
    parser.add_argument("--phrase", default="", help="Frase exacta que imprimió el dry-run.")
    args = parser.parse_args()
    try:
        root = repo_root()
        remaining, absent, main_sha, protected, temp_refs = verify(root)
        print(f"Repositorio: {REPO}")
        print(f"main verificado: {main_sha}")
        print(f"Manifiesto: issue #{ISSUE}")
        print(f"Candidatas registradas: {EXPECTED}")
        print(f"Ya ausentes: {len(absent)}")
        print(f"Candidatas presentes y revalidadas: {len(remaining)}")
        print("Ramas protegidas presentes: " + ", ".join(sorted(protected)))
        print("Ramas temporales presentes: " + (", ".join(sorted(temp_refs)) if temp_refs else "ninguna"))
        for item in remaining:
            print(f"OK  {item['branch']}  {item['sha']}")
        phrase = f"BORRAR {len(remaining)} RAMAS DE {REPO}"
        if not args.execute:
            print("\nDRY-RUN: no se eliminó ninguna rama.")
            print(f"Para borrar, volvé a ejecutar en modo delete y escribí: {phrase}")
            return 0
        if args.confirm != CONFIRM_TOKEN:
            raise CleanupError(f"Falta el token interno {CONFIRM_TOKEN}; no se borró nada.")
        if args.yes:
            if args.phrase != phrase:
                raise CleanupError("La frase de confirmación no coincide con el dry-run actual.")
        elif input(f"Escribí exactamente {phrase}: ").strip() != phrase:
            raise CleanupError("La confirmación no coincide; no se borró nada.")
        deleted = []
        for n, item in enumerate(remaining, 1):
            print(f"[{n}/{len(remaining)}] {item['branch']}", flush=True)
            delete_ref(root, item["branch"], item["sha"])
            deleted.append(item["branch"])
        for branch, sha in sorted(temp_refs.items()):
            print(f"[final] {branch}", flush=True)
            delete_ref(root, branch, sha)
            deleted.append(branch)
        lines = run(["git", "ls-remote", "--heads", "origin"], cwd=root).stdout.splitlines()
        after = {line.split("\t", 1)[1].removeprefix("refs/heads/") for line in lines if "\t" in line}
        if after != protected:
            raise CleanupError(
                f"Borrado parcial ({len(deleted)} refs); remanentes inesperados: {sorted(after - protected)}; "
                f"protegidas faltantes: {sorted(protected - after)}."
            )
        print(f"LIMPIEZA COMPLETA: {len(deleted)} refs eliminadas; permanecen {sorted(after)}.")
        return 0
    except (CleanupError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        print("Ejecución detenida; no se procesaron más ramas.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
