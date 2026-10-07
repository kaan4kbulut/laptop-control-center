#!/bin/sh
set -eu
cd "$(git rev-parse --show-toplevel)"
command -v python3 >/dev/null
mkdir -p .privacy-tools
if ! command -v gitleaks >/dev/null; then
  archive=$(mktemp)
  trap 'rm -f "$archive"' EXIT
  curl -fsSL 'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz' -o "$archive"
  printf '%s  %s\n' '551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb' "$archive" | sha256sum -c -
  tar -xzf "$archive" -C .privacy-tools gitleaks
  echo 'Gitleaks installed in .privacy-tools; add this directory to PATH for commits.'
fi
previous=$(git config --get core.hooksPath || true)
if [ -n "$previous" ] && [ "$previous" != .githooks ]; then
  echo 'Existing hooksPath detected; preserve it and manually chain .githooks/pre-commit.'
  exit 1
fi
git config core.hooksPath .githooks
echo 'Privacy pre-commit hook enabled.'
