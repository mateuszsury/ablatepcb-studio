from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import Converter


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Konwerter Gerber do masek PCB dla LightBurn")
    sub = result.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Przeanalizuj ZIP lub katalog")
    analyze.add_argument("source")
    generate = sub.add_parser("generate", help="Wygeneruj kompletny pakiet")
    generate.add_argument("source")
    generate.add_argument("--blank", nargs=2, type=float, metavar=("WIDTH", "HEIGHT"))
    generate.add_argument("--origin", nargs=2, type=float, default=(10.0, 10.0), metavar=("X", "Y"))
    generate.add_argument("--flip", choices=("left_right", "top_bottom"), default="left_right")
    generate.add_argument("--output", type=Path)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    converter = Converter()
    try:
        analysis = converter.analyze(args.source)
        if args.command == "analyze":
            print(json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False))
            return 0 if analysis.can_generate else 2
        blank = args.blank or (analysis.board_bounds.width, analysis.board_bounds.height)
        values = {
            "blankWidth": blank[0],
            "blankHeight": blank[1],
            "originX": args.origin[0],
            "originY": args.origin[1],
            "flip": args.flip,
        }
        destination = converter.generate(values, args.output)
        print(destination)
        return 0
    finally:
        converter.close()


if __name__ == "__main__":
    raise SystemExit(main())
