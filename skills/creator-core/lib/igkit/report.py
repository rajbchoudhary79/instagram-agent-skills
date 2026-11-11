"""Plain-text formatting helpers shared by the CLI tools."""

import json
import sys
import textwrap


def bar(score, width=20):
    if score is None:
        return ""
    n = int(round(width * max(0.0, min(100.0, score)) / 100.0))
    return "#" * n + "." * (width - n)


def box(text, width=60, title=None):
    inner = width - 4
    out = ["+" + "-" * (width - 2) + "+"]
    if title:
        out.append("| " + title.ljust(inner) + " |")
        out.append("|" + "-" * (width - 2) + "|")
    for para in text.splitlines() or [""]:
        wrapped = textwrap.wrap(para, inner) or [""]
        for ln in wrapped:
            out.append("| " + ln.ljust(inner) + " |")
    out.append("+" + "-" * (width - 2) + "+")
    return "\n".join(out)


def table(rows, headers):
    cols = [str(h) for h in headers]
    data = [[("" if c is None else str(c)) for c in r] for r in rows]
    widths = [max(len(cols[i]), *(len(r[i]) for r in data)) if data else len(cols[i]) for i in range(len(cols))]
    fmt = "  ".join("%-" + str(w) + "s" for w in widths)
    out = [fmt % tuple(cols), "  ".join("-" * w for w in widths)]
    out.extend(fmt % tuple(r) for r in data)
    return "\n".join(out)


def status_line(level, message):
    return "  %-5s %s" % (level, message)


def emit_json(obj):
    json.dump(obj, sys.stdout, indent=2, ensure_ascii=False, default=str)
    sys.stdout.write("\n")


def verdict(checks):
    """checks: list of dicts with 'level' in FAIL/WARN/PASS/INFO. Returns READY / REVIEW / BLOCKED."""
    levels = {c["level"] for c in checks}
    if "FAIL" in levels:
        return "BLOCKED"
    if "WARN" in levels:
        return "REVIEW"
    return "READY"


def render_checks(checks):
    return "\n".join(status_line(c["level"], c["message"]) for c in checks)
