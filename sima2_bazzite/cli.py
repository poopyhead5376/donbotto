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
    parser.add_argument("--use-ollama", action="store_true", help="Use local Ollama model for adaptive action generation")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", default="llama3.1")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("learn", help="Analyze mods and execute learning cycle")

    build = sub.add_parser("build", help="Build a structure from blueprint JSON")
    build.add_argument("--blueprint", type=Path, required=True)
    build.add_argument("--origin", nargs=3, type=int, metavar=("X", "Y", "Z"), required=True)

    research = sub.add_parser("research", help="Search YouTube tutorials for detected mod features")
    research.add_argument("--feature-limit", type=int, default=3)
    research.add_argument("--per-query-limit", type=int, default=3)
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
            use_ollama=args.use_ollama,
            ollama_url=args.ollama_url,
            ollama_model=args.ollama_model,
        )
    )
    try:
        if args.command == "learn":
            outputs = agent.execute_learning_cycle()
            for line in outputs:
                print(line)
        elif args.command == "build":
            outputs = agent.build(args.blueprint, tuple(args.origin))
            for line in outputs:
                print(line)
        else:
            findings = agent.research_tutorials(args.feature_limit, args.per_query_limit)
            for query, videos in findings.items():
                print(f"\n# {query}")
                for video in videos:
                    print(f"- {video.title} -> {video.url}")
    finally:
        agent.close()


if __name__ == "__main__":
    main()
