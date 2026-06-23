"""stdout — entry point.

    python run.py                 # full run: build the edition, then the site
    python run.py --collect-only  # just collect and print (no ranking/writing)
    python run.py --site-only     # rebuild the site from existing editions

The full run produces an edition under `edicoes/<date>/` (PT + EN) and rebuilds
the site under `docs/`. With a GEMINI_API_KEY set (in .env) the AI writes and
reviews the articles; without one it falls back so the run never fails.
"""

from __future__ import annotations

import argparse
import sys

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional — env vars can come from the shell / CI
    def load_dotenv(*_args, **_kwargs):
        return False


def _print_collection() -> None:
    from pipeline.collect import collect_all

    print("\n  stdout — coletando...\n" + "-" * 60)
    items = collect_all()
    items.sort(key=lambda i: i.popularity, reverse=True)
    print("\n" + "=" * 60)
    print(f"  {len(items)} itens coletados")
    print("=" * 60)
    for n, item in enumerate(items, 1):
        signal = f"▲{int(item.popularity)}" if item.popularity else ""
        print(f"\n{n:>2}. [{item.source}] {signal}")
        print(f"    {item.title}")
        print(f"    {item.url}")
    print()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # unicode-safe on Windows
    load_dotenv()

    parser = argparse.ArgumentParser(description="stdout — automated tech journal")
    parser.add_argument("--collect-only", action="store_true",
                        help="only collect and print items; skip everything else")
    parser.add_argument("--site-only", action="store_true",
                        help="rebuild the site from existing editions; skip collection")
    args = parser.parse_args()

    if args.collect_only:
        _print_collection()
        return

    if args.site_only:
        from pipeline.site import build_site
        build_site()
        return

    from pipeline.build import build_edition
    from pipeline.site import build_site

    build_edition()
    build_site()


if __name__ == "__main__":
    main()
