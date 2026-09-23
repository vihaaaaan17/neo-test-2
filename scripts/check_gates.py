#!/usr/bin/env python3
"""
Script to check that all gates in GATES.md are marked as completed ([x]).
"""
import re
import sys

def check_gates(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    # Find all gate lines: they start with "- [ ]" or "- [x]"
    # We are only interested in the gates that are part of the acceptance criteria.
    # The gates are listed under the phases (Phase D, Phase E, etc.)
    # We'll look for lines that match the pattern: "- [ ]" or "- [x]" followed by a gate description.
    pattern = r'^\s*- \[([ x])\].*'
    lines = content.split('\n')
    unchecked = []
    for line in lines:
        if re.match(pattern, line):
            # Extract the content inside the brackets
            match = re.search(r'\[([ x])\]', line)
            if match:
                status = match.group(1)
                if status == ' ':
                    unchecked.append(line.strip())

    if unchecked:
        print("UNCHECKED GATES FOUND:")
        for gate in unchecked:
            print(f"  {gate}")
        return False
    else:
        print("All gates are checked.")
        return True

if __name__ == "__main__":
    file_path = "GATES.md"
    if check_gates(file_path):
        sys.exit(0)
    else:
        sys.exit(1)