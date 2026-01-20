#!/usr/bin/env python3
import re
import sys
from pathlib import Path
from collections import defaultdict

COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)

def strip_comments(s: str) -> str:
    return re.sub(COMMENT_RE, "", s)

def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def norm_decls(block: str) -> str:
    # Normalize declarations for comparison (remove comments + whitespace)
    b = strip_comments(block)
    b = b.replace("\r\n", "\n")
    b = re.sub(r"\s*;\s*", ";", b)
    b = re.sub(r"\s*:\s*", ":", b)
    b = re.sub(r"\s*,\s*", ",", b)
    b = re.sub(r"\s*\{\s*", "{", b)
    b = re.sub(r"\s*\}\s*", "}", b)
    return b.strip()

def main(css_path: Path):
    text = css_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Collect comment header styles
    header_styles = defaultdict(int)
    for i, ln in enumerate(lines, start=1):
        s = ln.strip()
        if s.startswith("/*") and s.endswith("*/"):
            if "---" in s:
                header_styles["dash"] += 1
            elif "===" in s:
                header_styles["equals"] += 1
            elif "___" in s:
                header_styles["underscore"] += 1
            else:
                header_styles["other"] += 1

    # Very simple brace-based parser to capture top-level rules + @media scoped rules
    occurrences = defaultdict(list)  # (scope, selector) -> [(start_line, end_line, decl_norm)]
    scope_stack = ["GLOBAL"]
    i = 0
    n = len(text)

    # Helper to map char index -> line number
    char_to_line = []
    ln = 1
    for ch in text:
        char_to_line.append(ln)
        if ch == "\n":
            ln += 1

    def line_at(idx: int) -> int:
        if idx < 0:
            return 1
        if idx >= len(char_to_line):
            return char_to_line[-1]
        return char_to_line[idx]

    idx = 0
    while idx < n:
        # Skip comments
        if text.startswith("/*", idx):
            end = text.find("*/", idx + 2)
            idx = n if end == -1 else end + 2
            continue

        # Detect @media and push scope
        if text.startswith("@media", idx):
            brace = text.find("{", idx)
            if brace == -1:
                break
            cond = norm_ws(text[idx:brace])
            scope_stack.append(cond)
            idx = brace + 1
            continue

        # Detect other at-rules that open blocks (@keyframes etc.) and skip them as rules
        if text.startswith("@", idx):
            brace = text.find("{", idx)
            semi = text.find(";", idx)
            if semi != -1 and (brace == -1 or semi < brace):
                idx = semi + 1
                continue
            if brace == -1:
                break
            # push generic at-rule scope marker so braces still balance
            scope_stack.append("AT_RULE")
            idx = brace + 1
            continue

        # Detect closing brace
        if text[idx] == "}":
            if len(scope_stack) > 1:
                scope_stack.pop()
            idx += 1
            continue

        # Try to read selector until "{"
        brace = text.find("{", idx)
        if brace == -1:
            break

        chunk = text[idx:brace].strip()
        # If chunk contains '}' before '{', move forward
        if "}" in chunk:
            idx += 1
            continue

        # Must look like a selector (not empty, not at-rule)
        if chunk and not chunk.startswith("@"):
            # Find matching closing brace for this rule
            depth = 0
            j = brace
            while j < n:
                if text.startswith("/*", j):
                    end = text.find("*/", j + 2)
                    j = n if end == -1 else end + 2
                    continue
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1

            if j >= n:
                break

            decl_block = text[brace+1:j]
            decl_norm = norm_decls(decl_block)

            start_line = line_at(idx)
            end_line = line_at(j)

            scope = scope_stack[-1]
            selectors = [s.strip() for s in chunk.split(",") if s.strip()]
            for sel in selectors:
                occurrences[(scope, sel)].append((start_line, end_line, decl_norm))

            idx = j + 1
            continue

        idx = brace + 1

    # Report
    print(f"\nCSS audit for: {css_path}")
    print("\nComment header styles (counts):")
    for k in ("dash", "equals", "underscore", "other"):
        print(f"  {k:10}: {header_styles.get(k, 0)}")

    dups = [(k, v) for k, v in occurrences.items() if len(v) > 1 and k[0] != "AT_RULE"]
    print(f"\nDuplicate selector definitions: {len(dups)}")
    for (scope, sel), occs in sorted(dups, key=lambda x: (x[0][0], x[0][1]))[:200]:
        print(f"\n[{scope}] {sel}")
        for (a, b, dn) in occs:
            print(f"  lines {a}-{b}  (decl_len={len(dn)})")

    # Exact duplicates (same decl block repeated)
    exact = []
    for key, occs in occurrences.items():
        if len(occs) < 2:
            continue
        decl_map = defaultdict(list)
        for a, b, dn in occs:
            decl_map[dn].append((a, b))
        for dn, ranges in decl_map.items():
            if len(ranges) > 1 and dn:
                exact.append((key, ranges, dn))

    print(f"\nExact duplicate blocks (safe to remove one copy): {len(exact)}")
    for (scope, sel), ranges, _ in exact[:200]:
        print(f"\n[{scope}] {sel}")
        for (a, b) in ranges:
            print(f"  lines {a}-{b}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python tools/css_audit.py path/to/style.css")
        sys.exit(1)
    main(Path(sys.argv[1]))
