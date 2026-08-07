#!/usr/bin/env python3
"""Render twister.json as a markdown job summary for the xc32 CI workflow.

Usage: xc32_twister_summary.py <path-to-twister.json>
Prints markdown to stdout; the caller redirects it into $GITHUB_STEP_SUMMARY.
"""
import json
import sys
from collections import defaultdict

STATUS_LABEL = {
    "passed": "✅ Passed",
    "not run": "✅ Built OK",
    "error": "❌ Error",
    "failed": "❌ Failed",
    "skipped": "⏭️ Skipped",
    "filtered": "⏭️ Filtered",
}

# Statuses that represent a real problem, for the failures section / overview ordering.
BAD_STATUSES = {"error", "failed"}


def label(status):
    return STATUS_LABEL.get(status, status)


def main():
    if len(sys.argv) != 2:
        print("usage: xc32_twister_summary.py <twister.json>", file=sys.stderr)
        return 1

    with open(sys.argv[1]) as f:
        data = json.load(f)

    env = data.get("environment", {})
    suites = data.get("testsuites", [])

    counts = defaultdict(int)
    by_board = defaultdict(lambda: defaultdict(int))
    by_board_sample = {}
    failures = []

    for ts in suites:
        status = ts.get("status", "unknown")
        board = ts.get("platform", "?")
        sample = ts.get("name", "?")
        counts[status] += 1
        by_board[board][status] += 1
        by_board_sample[(board, sample)] = status
        if status in BAD_STATUSES:
            failures.append(ts)

    total = len(suites)
    bad_total = sum(counts[s] for s in BAD_STATUSES)

    out = []
    out.append("## XC32 Build Summary\n")
    out.append(
        f"**Zephyr:** `{env.get('zephyr_version', '?')}` &nbsp;|&nbsp; "
        f"**Toolchain:** {env.get('toolchain', '?')} &nbsp;|&nbsp; "
        f"**Run date:** {env.get('run_date', '?')}\n"
    )

    out.append("### Overview\n")
    out.append("| Status | Count |")
    out.append("|---|---|")
    for status in sorted(counts, key=lambda s: (s not in BAD_STATUSES, s)):
        out.append(f"| {label(status)} | {counts[status]} |")
    out.append(f"| **Total** | **{total}** |\n")

    if bad_total:
        out.append(f"### ❌ Failures ({bad_total})\n")
        out.append("| Board | Sample | Status | Reason |")
        out.append("|---|---|---|---|")
        for ts in sorted(failures, key=lambda t: (t.get("platform", ""), t.get("name", ""))):
            reason = (ts.get("reason") or "").replace("|", "\\|")
            out.append(
                f"| {ts.get('platform', '?')} | {ts.get('name', '?')} | "
                f"{label(ts.get('status'))} | {reason} |"
            )
        out.append("")
    else:
        out.append("### ✅ No failures\n")

    out.append("### Per-board breakdown\n")
    out.append("| Board | Built OK | Errors | Total |")
    out.append("|---|---|---|---|")
    for board in sorted(by_board):
        ok = by_board[board].get("passed", 0) + by_board[board].get("not run", 0)
        bad = sum(by_board[board].get(s, 0) for s in BAD_STATUSES)
        board_total = sum(by_board[board].values())
        out.append(f"| {board} | {ok} | {bad} | {board_total} |")
    out.append("")

    boards = sorted(by_board)
    samples = sorted({ts.get("name", "?") for ts in suites})
    out.append("<details>")
    out.append("<summary>Full board x sample matrix</summary>\n")
    header = "| Board | " + " | ".join(s.replace("sample.", "") for s in samples) + " |"
    sep = "|---|" + "---|" * len(samples)
    out.append(header)
    out.append(sep)
    for board in boards:
        row = [board]
        for sample in samples:
            status = by_board_sample.get((board, sample))
            row.append(label(status) if status else "⬜")
        out.append("| " + " | ".join(row) + " |")
    out.append("\n</details>")

    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
