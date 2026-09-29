#!/usr/bin/env python3
"""
scripts/scan_secrets.py

Secret leak detection scanner for NeosisLM.
Audits codebase files for accidental exposure of live API keys, AWS credentials,
private keys, and real authentication tokens.
Excludes test mocks and development dummy tokens.
"""

import os
import sys
import re
from typing import List, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Directories to scan
SCAN_DIRS = ["app", "scripts", "alembic", "docs"]

# File extensions to scan
SCAN_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml", ".ini", ".env.example", ".sh"}

# Patterns for genuine sensitive credentials
SUSPICIOUS_PATTERNS = [
    ("AWS Access Key ID", re.compile(r"(?<![A-Za-z0-9])(AKIA[0-9A-Z]{16})(?![A-Za-z0-9])")),
    ("Private Key Header", re.compile(r"-----BEGIN\s+(?:RSA|EC|OPENSSH|PGP|PRIVATE)\s+KEY-----")),
    ("OpenAI Live Secret Key", re.compile(r"(?<![A-Za-z0-9])sk-(?!ant-|mock|dummy|test|proj-)[A-Za-z0-9]{32,}(?![A-Za-z0-9])")),
    ("Anthropic Live Secret Key", re.compile(r"(?<![A-Za-z0-9])sk-ant-(?!mock|dummy|test)[A-Za-z0-9]{32,}(?![A-Za-z0-9])")),
    ("Slack Token", re.compile(r"(?<![A-Za-z0-9])xox[baprs]-(?!mock|test)[0-9A-Za-z]{10,}(?![A-Za-z0-9])")),
    ("GitHub Token", re.compile(r"(?<![A-Za-z0-9])(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9]{82})(?![A-Za-z0-9])")),
]

# Whitelist safe placeholder strings
ALLOWED_PLACEHOLDERS = {
    "super-secret-jwt-token-for-supabase-local-dev-only",
    "mock-secret",
    "mock-key",
    "password",
    "bolt://localhost:7687",
    "redis://localhost:6379",
}


def scan_file(filepath: str) -> List[Tuple[int, str, str]]:
    findings = []
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as fp:
            for line_no, line in enumerate(fp, start=1):
                # Ignore comment lines with obvious placeholder remarks
                if "mock" in line.lower() or "test" in line.lower() or "dummy" in line.lower():
                    continue
                for name, pattern in SUSPICIOUS_PATTERNS:
                    match = pattern.search(line)
                    if match:
                        matched_str = match.group(0)
                        if matched_str not in ALLOWED_PLACEHOLDERS:
                            findings.append((line_no, name, line.strip()))
    except Exception as e:
        print(f"Warning: could not read {filepath}: {e}", file=sys.stderr)
    return findings


def main() -> int:
    total_files_scanned = 0
    all_findings = []

    print("Running Secret Leak Detection Scan...")
    for d in SCAN_DIRS:
        dir_path = os.path.join(REPO_ROOT, d)
        if not os.path.exists(dir_path):
            continue
        for root, dirs, files in os.walk(dir_path):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".pytest_cache", ".venv", ".scratch", "node_modules"}]
            for f in files:
                ext = os.path.splitext(f)[1]
                if ext in SCAN_EXTENSIONS:
                    full_path = os.path.join(root, f)
                    total_files_scanned += 1
                    findings = scan_file(full_path)
                    if findings:
                        all_findings.append((full_path, findings))

    print(f"Scanned {total_files_scanned} files across {SCAN_DIRS}.")

    if all_findings:
        print(f"FAILED: Found {len(all_findings)} files with potential secret leaks:")
        for path, issues in all_findings:
            rel = os.path.relpath(path, REPO_ROOT)
            print(f"  File: {rel}")
            for line_no, name, snippet in issues:
                print(f"    Line {line_no} [{name}]: {snippet[:60]}...")
        return 1

    print("PASSED: Zero sensitive credentials or tokens detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
