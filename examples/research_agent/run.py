"""Run any version of the progressive example with a deterministic fake model."""

import argparse
import json

from examples.research_agent.versions import build_version, run_v0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=int, choices=range(5), default=4)
    parser.add_argument(
        "--question",
        default="How can heatwaves affect electricity demand?",
    )
    args = parser.parse_args()

    if args.version == 0:
        print(run_v0(args.question))
        return

    graph = build_version(args.version)
    result = graph.invoke({"question": args.question, "attempts": 0, "trace": []})
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
