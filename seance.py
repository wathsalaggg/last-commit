#!/usr/bin/env python3
"""Hold a séance for a dead GitHub repo.

    python3 seance.py atom/atom
    python3 seance.py https://github.com/request/request --no-voice
    python3 seance.py --all            # every repo in repos.txt
    python3 seance.py --facts-only bower/bower

Writes site/data/<owner>__<repo>.json (+ site/audio/<owner>__<repo>.mp3)
and rebuilds site/data/index.json for the graveyard page.
"""

import argparse
import json
import sys
import time

from lastcommit import config, ghost, github, voice


def slug(full_name: str) -> str:
    return full_name.replace("/", "__")


def rebuild_index() -> int:
    entries = []
    for path in sorted(config.DATA_DIR.glob("*__*.json")):
        d = json.loads(path.read_text())
        f = d["facts"]
        entries.append({
            "slug": path.stem,
            "name": f["full_name"],
            "born": f["born"],
            "died": f["died"],
            "epitaph": d["ghost"]["epitaph"] if d.get("ghost") else "",
            "stars": f["stars"],
        })
    entries.sort(key=lambda e: e["died"])
    (config.DATA_DIR / "index.json").write_text(json.dumps(entries, indent=2) + "\n")
    return len(entries)


def hold_seance(target: str, *, use_voice: bool, facts_only: bool, force: bool) -> None:
    print(f"🕯  Summoning {target} ...", flush=True)
    facts = github.gather(target)
    s = slug(facts["full_name"])
    out = config.DATA_DIR / f"{s}.json"
    existing = json.loads(out.read_text()) if out.exists() else {}

    record = {"facts": facts, "ghost": existing.get("ghost"), "audio": existing.get("audio")}

    if not facts_only and (force or not record["ghost"]):
        t = time.time()
        record["ghost"] = ghost.summon(facts)
        record["ghost"]["generated_at"] = facts["fetched_at"]
        print(f"   ghost written in {time.time() - t:.0f}s "
              f"({record['ghost']['provider']}:{record['ghost']['model']})")
        print(f"   EPITAPH: {record['ghost']['epitaph']}")
        record["audio"] = None  # text changed, old audio no longer matches

    if use_voice and record["ghost"] and not record["audio"]:
        mp3 = config.AUDIO_DIR / f"{s}.mp3"
        voice.speak(record["ghost"]["monologue"], mp3)
        record["audio"] = f"audio/{mp3.name}"
        print(f"   voice saved to site/{record['audio']}")

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    print(f"   saved site/data/{out.name}")


def main() -> int:
    config.load_dotenv()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repos", nargs="*", help="owner/repo or GitHub URL")
    p.add_argument("--all", action="store_true", help="use every repo in repos.txt")
    p.add_argument("--no-voice", action="store_true", help="skip ElevenLabs")
    p.add_argument("--facts-only", action="store_true", help="only refresh GitHub facts")
    p.add_argument("--force", action="store_true", help="rewrite the ghost even if one exists")
    args = p.parse_args()

    targets = list(args.repos)
    if args.all:
        lines = (config.ROOT / "repos.txt").read_text().splitlines()
        targets += [l.split("#")[0].strip() for l in lines if l.split("#")[0].strip()]
    if not targets:
        p.print_help()
        return 1

    failed = 0
    for t in targets:
        try:
            hold_seance(t, use_voice=not (args.no_voice or args.facts_only),
                        facts_only=args.facts_only, force=args.force)
        except Exception as e:  # keep going: one restless spirit shouldn't stop the rest
            failed += 1
            print(f"   ✗ {t}: {e}", file=sys.stderr)
    print(f"🪦 Graveyard has {rebuild_index()} graves.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
