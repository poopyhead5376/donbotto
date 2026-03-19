from __future__ import annotations

import argparse
from pathlib import Path

from sima2_bazzite.agent import AgentConfig, Sima2BazziteAgent
from sima2_bazzite.network import auto_detect_rcon_host


COMMANDS_REQUIRING_MODS_DIR = {"learn", "research", "build-from-tutorial"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SIMA2 clone for modded Minecraft on Bazzite")
    parser.add_argument("--mods-dir", type=Path)
    parser.add_argument("--knowledge-db", type=Path, default=Path("./data/knowledge.sqlite3"))
    parser.add_argument("--rcon-host", default="auto", help="RCON host/IP. Use 'auto' to detect the local IP automatically")
    parser.add_argument("--rcon-port", type=int, default=25575)
    parser.add_argument("--rcon-password", default="")
    parser.add_argument("--offline", action="store_true", help="Skip live RCON execution and print planned commands instead")
    parser.add_argument("--use-ollama", action="store_true", help="Use local Ollama model for adaptive action generation")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--ollama-model", default="llama3.1")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("learn", help="Analyze mods and execute learning cycle")

    build = sub.add_parser("build-from-tutorial", help="Search YouTube tutorials and autonomously build a matching structure")
    build.add_argument("--query", required=True, help="Structure to search for, such as 'starter house' or 'watch tower'")
    build.add_argument("--origin", nargs=3, type=int, metavar=("X", "Y", "Z"), required=True)

    research = sub.add_parser("research", help="Search YouTube tutorials for detected mod features")
    research.add_argument("--feature-limit", type=int, default=3)
    research.add_argument("--per-query-limit", type=int, default=3)

    sub.add_parser("show-ip", help="Print the auto-detected local IP that would be used for RCON")
    args = parser.parse_args()
    if args.command in COMMANDS_REQUIRING_MODS_DIR and args.mods_dir is None:
        parser.error("--mods-dir is required for learn, research, and build-from-tutorial")
    return args


def main() -> None:
    args = parse_args()
    if args.command == "show-ip":
        print(auto_detect_rcon_host())
        return

    agent = Sima2BazziteAgent(
        AgentConfig(
            mods_dir=args.mods_dir,
            knowledge_db=args.knowledge_db,
            rcon_host=args.rcon_host,
            rcon_port=args.rcon_port,
            rcon_password=args.rcon_password,
            offline=args.offline,
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
        elif args.command == "build-from-tutorial":
            plan, outputs = agent.build_from_tutorial(args.query, tuple(args.origin))
            print(f"Tutorial query: {plan.query}")
            print(f"Rationale: {plan.rationale}")
            if plan.source_video:
                print(f"Source video: {plan.source_video.title} -> {plan.source_video.url}")
            print(f"Blocks placed: {len(plan.placements)}")
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
