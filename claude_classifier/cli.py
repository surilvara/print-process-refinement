"""CLI dispatcher: ``python -m claude_classifier <subcommand>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from loguru import logger

from claude_classifier import db, pass1, pass2


def cmd_pass1(args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    if not input_path.is_dir():
        logger.error(f"Input is not a directory: {input_path}")
        return 1
    run_id = pass1.submit(input_path)
    print(run_id)
    return 0


def cmd_pass1_collect(args: argparse.Namespace) -> int:
    try:
        pass1.collect(args.run)
    except SystemExit as e:
        return int(e.code) if e.code else 1
    return 0


def cmd_pass2(args: argparse.Namespace) -> int:
    pass2_run_id = pass2.run(args.run)
    print(pass2_run_id)
    return 0


def cmd_list(_: argparse.Namespace) -> int:
    with db.connect() as conn:
        rows = db.list_runs(conn)
    if not rows:
        print("(no runs)")
        return 0
    headers = [
        "run_id",
        "publication",
        "issue",
        "pages",
        "pass1",
        "pass1_cost",
        "pass2_runs",
        "pass2_cost",
        "submitted",
    ]
    print("\t".join(headers))
    for r in rows:
        p1_cost = r["pass1_cost_usd"]
        p2_cost = r["pass2_cost_usd_total"]
        print(
            "\t".join(
                str(x) if x is not None else "-"
                for x in [
                    r["run_id"],
                    r["publication_name"],
                    r["issue_date"],
                    r["page_count"],
                    r["pass1_status"],
                    f"${p1_cost:.4f}" if p1_cost is not None else "-",
                    r["pass2_run_count"],
                    f"${p2_cost:.4f}" if p2_cost else "-",
                    r["submitted_at"],
                ]
            )
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="claude_classifier",
        description="Two-pass Claude-based magazine page classification.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_pass1 = sub.add_parser("pass1", help="Submit pass 1 batch for a magazine folder.")
    p_pass1.add_argument("--input", required=True, help="Path to inputs/<folder>/")
    p_pass1.set_defaults(func=cmd_pass1)

    p_collect = sub.add_parser(
        "pass1-collect",
        help="Poll the submitted batch; on completion write pass1/*.json.",
    )
    p_collect.add_argument("--run", required=True, help="run_id returned by `pass1`")
    p_collect.set_defaults(func=cmd_pass1_collect)

    p_pass2 = sub.add_parser("pass2", help="Run pass 2 against a completed pass-1 run.")
    p_pass2.add_argument("--run", required=True)
    p_pass2.set_defaults(func=cmd_pass2)

    p_list = sub.add_parser("list", help="List runs and their status.")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
