#!/usr/bin/env python3
"""Content calendar: plan slots, track ideas and publishing status, check the mix.

  planner.py plan --start 2026-11-16 --weeks 1        build a week of slots
  planner.py plan --month 2026-12                      build a month
  planner.py list [--from D] [--to D] [--status planned]
  planner.py assign c-0003 --topic "Feed in the morning, bake after work" --hook "..." [--format reel]
  planner.py status c-0003 drafted
  planner.py move c-0003 --date 2026-11-19
  planner.py add --date 2026-11-20 --format carousel --topic "..." [--pillar P] [--type educational]
  planner.py remove c-0003
  planner.py idea add "Overnight fridge proof test" [--pillar "Bake schedules"]
  planner.py idea list
  planner.py idea use i-0002 c-0005                    put an idea into a slot
  planner.py balance [--from D] [--to D]               actual vs target mix
  planner.py export --md week.md | --csv week.csv

Storage: <workspace>/calendar.json (./.creator-content-kit/ in a project, else
~/.creator-content-kit/), or --file PATH. Pillars, mix, cadence and posting days
come from the creator profile, falling back to mix.json.

Status flow: slot -> planned -> drafted -> approved -> scheduled -> published (or skipped).
'approved' and later are set only when the creator says so.
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys

import _bootstrap  # noqa: F401
from igkit import paths, profile as P, report as R

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUSES = ["slot", "planned", "drafted", "approved", "scheduled", "published", "skipped"]
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def defaults():
    return paths.load_json(os.path.join(HERE, "mix.json"))


def cal_path(explicit=None):
    return os.path.abspath(explicit) if explicit else os.path.join(paths.workspace_dir(), "calendar.json")


def load(path):
    if os.path.isfile(path):
        return paths.load_json(path)
    return {"version": 1, "items": [], "ideas": [], "seq": {"c": 0, "i": 0}}


def save(cal, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cal["items"].sort(key=lambda x: (x["date"], x.get("time") or "", x["id"]))
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cal, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def next_id(cal, kind):
    cal.setdefault("seq", {"c": 0, "i": 0})
    cal["seq"][kind] += 1
    return "%s-%04d" % (kind, cal["seq"][kind])


def smooth_round_robin(weights, n):
    """Deterministic interleaving that hits the target shares and avoids clumping."""
    names = [k for k, w in weights.items() if w > 0]
    if not names:
        return [None] * n
    total = float(sum(weights[k] for k in names))
    current = {k: 0.0 for k in names}
    out = []
    for _ in range(n):
        for k in names:
            current[k] += weights[k] / total
        pick = max(names, key=lambda k: current[k])
        current[pick] -= 1.0
        out.append(pick)
    return out


def targets(profile):
    d = defaults()
    pillars = {p["name"]: p.get("share", 0) for p in (P.get(profile or {}, "niche.pillars") or [])
               if isinstance(p, dict) and p.get("name")}
    if pillars and not any(pillars.values()):
        pillars = {k: 1 for k in pillars}
    mix = P.get(profile or {}, "content.mix") or d["mix"]
    formats = P.get(profile or {}, "content.formats_preferred") or d["formats"]
    fweights = {f: d["format_weights"].get(f, 1) for f in formats if f != "story"}
    return {
        "pillars": pillars or {"(no pillars set)": 1},
        "mix": {k: v for k, v in mix.items() if v},
        "formats": fweights,
        "per_week": P.get(profile or {}, "content.posts_per_week") or d["posts_per_week"],
        "days": P.get(profile or {}, "content.posting_days") or d["posting_days"],
        "times": P.get(profile or {}, "content.best_times") or [],
    }


def slot_dates(start, end, per_week, days):
    days = [d for d in DAYS if d in days] or DAYS
    out = []
    cur = start - dt.timedelta(days=start.weekday())
    while cur <= end:
        week = [cur + dt.timedelta(days=DAYS.index(d)) for d in days]
        if per_week < len(week):
            step = len(week) / float(per_week)
            week = [week[int(i * step)] for i in range(per_week)]
        elif per_week > len(week):
            week = (week * (per_week // len(week) + 1))[:per_week]
            week.sort()
        out.extend(d for d in week if start <= d <= end)
        cur += dt.timedelta(days=7)
    return out


def cmd_plan(args, cal, profile):
    t = targets(profile)
    if args.month:
        y, m = map(int, args.month.split("-"))
        start = dt.date(y, m, 1)
        end = (dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1))
    else:
        start = dt.date.fromisoformat(args.start) if args.start else dt.date.today()
        end = start + dt.timedelta(days=7 * args.weeks - 1)
    per_week = args.per_week or t["per_week"]
    days = args.days.split(",") if args.days else t["days"]
    dates = slot_dates(start, end, per_week, days)
    existing = {(i["date"]) for i in cal["items"]}
    if args.replace:
        cal["items"] = [i for i in cal["items"] if not (start.isoformat() <= i["date"] <= end.isoformat() and i["status"] == "slot")]
        existing = {(i["date"]) for i in cal["items"]}
    dates = [d for d in dates if d.isoformat() not in existing or args.allow_double]
    pill = smooth_round_robin(t["pillars"], len(dates))
    mix = smooth_round_robin(t["mix"], len(dates))
    fmts = smooth_round_robin(t["formats"], len(dates))
    created = []
    for k, d in enumerate(dates):
        item = {"id": next_id(cal, "c"), "date": d.isoformat(), "time": t["times"][k % len(t["times"])] if t["times"] else "",
                "format": fmts[k], "pillar": pill[k], "type": mix[k], "topic": "", "hook": "", "status": "slot",
                "notes": "", "history": [{"status": "slot", "at": dt.date.today().isoformat()}]}
        cal["items"].append(item)
        created.append(item)
    print("Planned %d slots %s to %s (%d/week on %s)." % (len(created), start, end, per_week, ",".join(days)))
    if len(dates) == 0:
        print("No new slots: dates already have items (use --replace or --allow-double).")
    show(created)
    return True


def show(items):
    if not items:
        print("(nothing)")
        return
    print(R.table([(i["id"], i["date"], dt.date.fromisoformat(i["date"]).strftime("%a"), i.get("time", ""), i["format"],
                    i["pillar"], i["type"], i["status"], (i.get("topic") or "")[:30]) for i in items],
                  ["id", "date", "day", "time", "format", "pillar", "type", "status", "topic"]))


def find(cal, iid):
    for i in cal["items"]:
        if i["id"] == iid:
            return i
    sys.exit("no calendar item %s" % iid)


def set_status(item, status):
    if status not in STATUSES:
        sys.exit("status must be one of: " + ", ".join(STATUSES))
    item["status"] = status
    item.setdefault("history", []).append({"status": status, "at": dt.date.today().isoformat()})


def in_range(i, a, b):
    return (not a or i["date"] >= a) and (not b or i["date"] <= b)


def balance(cal, profile, a=None, b=None):
    t = targets(profile)
    items = [i for i in cal["items"] if in_range(i, a, b) and i["status"] != "skipped"]
    out = {}
    for key, field in (("pillars", "pillar"), ("mix", "type"), ("formats", "format")):
        tgt = t[key]
        tot = float(sum(tgt.values())) or 1.0
        counts = {}
        for i in items:
            counts[i.get(field)] = counts.get(i.get(field), 0) + 1
        rows = []
        for name in sorted(set(tgt) | set(counts)):
            actual = counts.get(name, 0) / len(items) if items else 0
            target = tgt.get(name, 0) / tot
            rows.append({"name": name, "count": counts.get(name, 0), "actual": round(actual, 2), "target": round(target, 2),
                         "delta": round(actual - target, 2)})
        out[field] = rows
    return {"items": len(items), "balance": out}


def export(cal, a, b, md=None, csvp=None):
    items = [i for i in cal["items"] if in_range(i, a, b)]
    if md:
        lines = ["# Content calendar %s to %s" % (a or (items[0]["date"] if items else ""), b or (items[-1]["date"] if items else "")), "",
                 "| date | day | format | pillar | type | topic | hook | status |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for i in items:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                i["date"], dt.date.fromisoformat(i["date"]).strftime("%a"), i["format"], i["pillar"], i["type"],
                (i.get("topic") or "_open_").replace("|", "/"), (i.get("hook") or "").replace("|", "/"), i["status"]))
        with open(md, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    if csvp:
        with open(csvp, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "date", "time", "format", "pillar", "type", "topic", "hook", "status", "notes"])
            for i in items:
                w.writerow([i["id"], i["date"], i.get("time", ""), i["format"], i["pillar"], i["type"], i.get("topic", ""),
                            i.get("hook", ""), i["status"], i.get("notes", "")])
    return len(items)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", help="calendar.json path")
    ap.add_argument("--profile")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan")
    p.add_argument("--start")
    p.add_argument("--weeks", type=int, default=1)
    p.add_argument("--month", help="YYYY-MM")
    p.add_argument("--per-week", type=int)
    p.add_argument("--days", help="comma list, e.g. mon,wed,fri")
    p.add_argument("--replace", action="store_true", help="replace empty slots in the range")
    p.add_argument("--allow-double", action="store_true", help="allow two items on one date")
    ls = sub.add_parser("list")
    ls.add_argument("--from", dest="frm")
    ls.add_argument("--to")
    ls.add_argument("--status")
    asg = sub.add_parser("assign")
    asg.add_argument("id")
    for f in ("topic", "hook", "format", "pillar", "type", "notes"):
        asg.add_argument("--" + f)
    st = sub.add_parser("status")
    st.add_argument("id")
    st.add_argument("status")
    mv = sub.add_parser("move")
    mv.add_argument("id")
    mv.add_argument("--date", required=True)
    ad = sub.add_parser("add")
    ad.add_argument("--date", required=True)
    ad.add_argument("--format", required=True)
    ad.add_argument("--topic", default="")
    ad.add_argument("--hook", default="")
    ad.add_argument("--pillar", default="")
    ad.add_argument("--type", default="educational")
    ad.add_argument("--status", default="planned")
    rm = sub.add_parser("remove")
    rm.add_argument("id")
    idea = sub.add_parser("idea")
    isub = idea.add_subparsers(dest="icmd")
    ia = isub.add_parser("add")
    ia.add_argument("text")
    ia.add_argument("--pillar", default="")
    ia.add_argument("--format", default="")
    isub.add_parser("list")
    iu = isub.add_parser("use")
    iu.add_argument("idea_id")
    iu.add_argument("slot_id")
    bal = sub.add_parser("balance")
    bal.add_argument("--from", dest="frm")
    bal.add_argument("--to")
    ex = sub.add_parser("export")
    ex.add_argument("--md")
    ex.add_argument("--csv")
    ex.add_argument("--from", dest="frm")
    ex.add_argument("--to")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2

    path = cal_path(args.file)
    cal = load(path)
    profile, _, _ = P.load(args.profile)
    changed = False

    if args.cmd == "plan":
        changed = cmd_plan(args, cal, profile)
    elif args.cmd == "list":
        items = [i for i in cal["items"] if in_range(i, args.frm, args.to) and (not args.status or i["status"] == args.status)]
        if args.json:
            R.emit_json(items)
        else:
            show(items)
            print("\n%d ideas in the backlog. Calendar: %s" % (len(cal["ideas"]), path))
    elif args.cmd == "assign":
        it = find(cal, args.id)
        for f in ("topic", "hook", "format", "pillar", "type", "notes"):
            if getattr(args, f) is not None:
                it[f] = getattr(args, f)
        if it["status"] == "slot" and it.get("topic"):
            set_status(it, "planned")
        changed = True
        show([it])
    elif args.cmd == "status":
        it = find(cal, args.id)
        set_status(it, args.status)
        changed = True
        show([it])
    elif args.cmd == "move":
        it = find(cal, args.id)
        dt.date.fromisoformat(args.date)
        it["date"] = args.date
        changed = True
        show([it])
    elif args.cmd == "add":
        dt.date.fromisoformat(args.date)
        it = {"id": next_id(cal, "c"), "date": args.date, "time": "", "format": args.format, "pillar": args.pillar,
              "type": args.type, "topic": args.topic, "hook": args.hook, "status": args.status, "notes": "",
              "history": [{"status": args.status, "at": dt.date.today().isoformat()}]}
        cal["items"].append(it)
        changed = True
        show([it])
    elif args.cmd == "remove":
        it = find(cal, args.id)
        cal["items"].remove(it)
        changed = True
        print("removed %s" % args.id)
    elif args.cmd == "idea":
        if args.icmd == "add":
            idea = {"id": next_id(cal, "i"), "text": args.text, "pillar": args.pillar, "format": args.format,
                    "added": dt.date.today().isoformat()}
            cal["ideas"].append(idea)
            changed = True
            print("added %s" % idea["id"])
        elif args.icmd == "use":
            idea = next((x for x in cal["ideas"] if x["id"] == args.idea_id), None)
            if not idea:
                sys.exit("no idea %s" % args.idea_id)
            it = find(cal, args.slot_id)
            it["topic"] = idea["text"]
            if idea.get("pillar"):
                it["pillar"] = idea["pillar"]
            if idea.get("format"):
                it["format"] = idea["format"]
            if it["status"] == "slot":
                set_status(it, "planned")
            cal["ideas"].remove(idea)
            changed = True
            show([it])
        else:
            if args.json:
                R.emit_json(cal["ideas"])
            else:
                print(R.table([(x["id"], x.get("pillar", ""), x.get("format", ""), x["text"][:50]) for x in cal["ideas"]],
                              ["id", "pillar", "format", "idea"]) if cal["ideas"] else "(no ideas)")
    elif args.cmd == "balance":
        res = balance(cal, profile, args.frm, args.to)
        if args.json:
            R.emit_json(res)
        else:
            print("MIX CHECK  %d items (skipped excluded)" % res["items"])
            for field, rows in res["balance"].items():
                print("\n" + field.upper())
                print(R.table([(r["name"], r["count"], "%d%%" % round(100 * r["actual"]), "%d%%" % round(100 * r["target"]),
                                "%+d" % round(100 * r["delta"]) + ("  <-- off" if abs(r["delta"]) >= 0.15 else ""))
                               for r in rows], ["name", "n", "actual", "target", "delta"]))
    elif args.cmd == "export":
        if not (args.md or args.csv):
            sys.exit("give --md and/or --csv")
        n = export(cal, args.frm, args.to, args.md, args.csv)
        print("exported %d items" % n)

    if changed:
        save(cal, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
