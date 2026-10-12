#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "${1:-}" ]]; then
  echo "Usage: $0 PATH/TO/SHA256SUMS" >&2
  exit 2
fi

manifest=$1
if [[ ! -f "$manifest" ]]; then
  echo "Checksum manifest not found: $manifest" >&2
  exit 2
fi

if ! command -v sha256sum >/dev/null 2>&1; then
  echo "sha256sum is required to verify this release manifest." >&2
  exit 2
fi

manifest_dir="$(cd -- "$(dirname -- "$manifest")" && pwd)"
manifest_name="$(basename -- "$manifest")"

# sha256sum entries are stored as names relative to the directory used to
# create the manifest. Always verify from that same directory, not the caller's
# working directory (the release job and local callers may differ).
(
  cd -- "$manifest_dir"
  sha256sum --check --strict "$manifest_name"
)
