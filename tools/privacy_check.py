#!/usr/bin/env python3
"""Publication guard. Never prints matched personal values or credentials."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SAFE_USERS = {'user', 'username', 'alice', 'bob', 'runner', 'test', 'tester', 'a', 'u', 'demo', 'developer', 'example', 'root', 'foo'}
HOME = re.compile(rb'/(?:home|Users)/([A-Za-z0-9_.-]+)|[A-Z]:\\Users\\([A-Za-z0-9_.-]+)')
EMAIL = re.compile(rb'[A-Za-z0-9._%+-]+@(?:gmail|hotmail|outlook|yahoo|protonmail|icloud|yandex)\.[A-Za-z.]+', re.I)
MEDIA = {'.png', '.jpg', '.jpeg', '.webp', '.pdf', '.zip', '.7z', '.tar', '.gz', '.exe', '.dmg', '.appimage', '.wav', '.mp3', '.mp4'}

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def inspect(path, raw, approved):
    findings = []
    parts = Path(path).parts
    base = Path(path).name.lower()
    if base.endswith(('.db', '.sqlite', '.sqlite3', '.log', '.jsonl', '.pem', '.p12', '.pfx')) or base in ('host.token', 'id_rsa', 'id_ed25519', 'credentials.json', '.env') or (base.startswith('.env.') and not base.endswith(('.example', '.sample', '.template'))):
        findings.append('runtime/credential file')
    if any(p in ('node_modules', '.venv', '__pycache__', '.aws', '.ssh', 'özel-yedekler') for p in parts):
        findings.append('private/generated directory')
    for match in HOME.finditer(raw):
        login = (match.group(1) or match.group(2)).decode(errors='replace')
        if login.lower() not in SAFE_USERS:
            findings.append('personal home path')
            break
    if EMAIL.search(raw):
        findings.append('personal email')
    if Path(path).suffix.lower() in MEDIA and hashlib.sha256(raw).hexdigest() not in approved:
        findings.append('unreviewed media/archive; privacy-assets.json requires manual review')
    return findings

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--staged', action='store_true')
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--skip-gitleaks', action='store_true', help='Use only when Gitleaks is run separately by CI')
    args = parser.parse_args()
    policy = json.loads((ROOT / '.privacy-policy.json').read_text())
    if args.publish and policy['publication'] == 'private-only':
        print('BLOCKED: this repository contains a private knowledge/preferences workspace.')
        return 1
    approved = set(json.loads((ROOT / 'privacy-assets.json').read_text())['reviewed_sha256'])
    paths = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z') if args.staged else git('ls-files', '-z')
    failures = []
    for entry in paths.split(b'\0'):
        if not entry:
            continue
        path = entry.decode(errors='strict')
        raw = git('show', ':' + path)
        for kind in inspect(path, raw, approved):
            failures.append((path, kind))
    if args.staged:
        identity = git('var', 'GIT_AUTHOR_IDENT').decode()
        if not identity.startswith(policy['git_author'] + ' <') or '@users.noreply.github.com>' not in identity:
            failures.append(('Git author', 'use the configured public alias and GitHub noreply email before committing'))
    for path, kind in failures:
        print('BLOCKED:', path, '—', kind)
    if failures:
        return 1
    if not args.skip_gitleaks:
        binary = shutil.which('gitleaks') or (str(ROOT / '.privacy-tools/gitleaks') if (ROOT / '.privacy-tools/gitleaks').is_file() else None)
        if not binary:
            print('BLOCKED: Gitleaks missing. Run tools/install-privacy-hooks.sh.')
            return 1
        command = [binary, 'git', str(ROOT), '--redact=100', '--no-banner', '--ignore-gitleaks-allow', '--gitleaks-ignore-path', str(ROOT / '.gitleaksignore')]
        command += ['--staged'] if args.staged else ['--log-opts=--all']
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            print('BLOCKED: Gitleaks secret scan failed; inspect locally with --redact=100.')
            return 1
    print('PASS: privacy checks; matched values are never logged. Manual review is still required for new media and personal prose.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
