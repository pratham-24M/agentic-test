#!/usr/bin/env python3
"""Check every line of a requirements file against PyPI for Python 3.11."""
import json
import re
import sys
import urllib.error
import urllib.request

from packaging.specifiers import SpecifierSet
from packaging.version import Version

TARGET = Version("3.11")


def fetch(name, version):
    """Return release JSON, or None if PyPI answers 404."""
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def parse(line):
    """'name==version' -> (name, version); None if not a pinned line."""
    line = line.split("#")[0].strip()
    m = re.match(r"^([A-Za-z0-9._-]+)(?:\[[^\]]*\])?\s*==\s*([^\s;]+)", line)
    return (m.group(1), m.group(2)) if m else None


def min_python(spec):
    """Lowest Python version a SpecifierSet allows (from >=, >, ~=, ==)."""
    lows = [Version(s.version.replace(".*", ""))
            for s in spec if s.operator in (">=", ">", "~=", "==")]
    return max(lows) if lows else Version("0")


def main(path):
    with open(path) as f:
        lines = [l for l in f.read().splitlines() if l.strip()]

    not_found = 0
    incompatible = 0
    highest = None  # (Version, "name==version", raw specifier)

    for line in lines:
        parsed = parse(line)
        data = fetch(*parsed) if parsed else None
        if data is None:
            not_found += 1
            continue
        rp = (data["info"].get("requires_python") or "").strip()
        if not rp:
            continue  # no requires_python -> compatible, can't be "highest"
        spec = SpecifierSet(rp)
        if not spec.contains(TARGET, prereleases=True):
            incompatible += 1
        low = min_python(spec)
        if highest is None or low > highest[0]:
            highest = (low, f"{parsed[0]}=={parsed[1]}", rp)

    print(f"Dependencies checked: {len(lines)}")
    print(f"Not found on PyPI: {not_found}")
    print(f"Incompatible with Python 3.11: {incompatible}")
    if highest:
        print(f"Highest requirement: {highest[1]} (>={highest[0]})")
    else:
        print("Highest requirement: none")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "requirements.txt")