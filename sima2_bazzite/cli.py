from __future__ import annotations

import argparse
from pathlib import Path

from sima2_bazzite.agent import AgentConfig, Sima2BazziteAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIMA2 clone for modded Minecraft on Bazzite")
    parser.add_argument("--mods-dir", type=Path, required=True)
    parser.add_argument("--knowledge-db", type=Path, default=Path("./data/knowledge.sqlite3"))
    parser.add_argument("--rcon-host", default="127.0.0.1")
    parser.add_argument("--rcon-port", type=int, default=25575)
    parser.add_argument("--rcon-password", required=True)

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("learn", help="Analyze mods and execute learning cycle")

    build = sub.add_parser("build", help="Build a structure from blueprint JSON")
    build.add_argument("--blueprint", type=Path, required=True)
    build.add_argument("--origin", nargs=3, type=int, metavar=("X", "Y", "Z"), required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    agent = Sima2BazziteAgent(
        AgentConfig(
            mods_dir=args.mods_dir,
            knowledge_db=args.knowledge_db,
            rcon_host=args.rcon_host,
            rcon_port=args.rcon_port,
            rcon_password=args.rcon_password,
        )
    )
    try:
        if args.command == "learn":
            outputs = agent.execute_learning_cycle()
        else:
            outputs = agent.build(args.blueprint, tuple(args.origin))
        for line in outputs:
            print(line)
    finally:
        agent.close()


if __name__ == "__main__":
    main()
