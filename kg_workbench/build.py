from __future__ import annotations

import argparse

from kg_workbench.config import WorkbenchConfig, load_config
from kg_workbench.pipeline import build_from_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one KG per parsed Markdown file.")
    parser.add_argument("--config", default=None, help="YAML config path.")
    parser.add_argument("--input", default=None, help="Markdown file or JSON manifest path.")
    parser.add_argument("--working-dir", default=None)
    parser.add_argument("--graph-backend", default=None, choices=["kuzu"])
    parser.add_argument("--export", default=None, choices=["json"])
    parser.add_argument(
        "--extractor",
        default=None,
        choices=["heuristic", "llm"],
        help="Use offline heuristic extraction or async OpenAI-compatible LLM extraction.",
    )
    parser.add_argument("--llm-model", default=None, help="Model name for --extractor llm.")
    parser.add_argument("--llm-api-key", default=None, help="API key; defaults to OPENAI_API_KEY.")
    parser.add_argument("--llm-base-url", default=None, help="Base URL; defaults to OPENAI_BASE_URL or OpenAI.")
    parser.add_argument("--llm-temperature", type=float, default=None)
    parser.add_argument(
        "--split-text-nodes",
        action="store_true",
        help="Split long text nodes instead of preserving parsed markdown units.",
    )
    args = parser.parse_args()

    if args.config:
        config = load_config(args.config)
    elif args.input:
        config = WorkbenchConfig(input_path=args.input)
    else:
        parser.error("Either --config or --input is required.")

    if args.input is not None:
        config.input_path = args.input
    if args.working_dir is not None:
        config.working_dir = args.working_dir
    if args.graph_backend is not None:
        config.graph_backend = args.graph_backend
    if args.export is not None:
        config.export = args.export
    if args.split_text_nodes:
        config.split_text_nodes = True
    if args.extractor is not None:
        config.extractor = args.extractor
    if args.llm_model is not None:
        config.llm_model = args.llm_model
    if args.llm_api_key is not None:
        config.llm_api_key = args.llm_api_key
    if args.llm_base_url is not None:
        config.llm_base_url = args.llm_base_url
    if args.llm_temperature is not None:
        config.llm_temperature = args.llm_temperature

    results = build_from_config(
        config
    )
    for result in results:
        print(
            f"{result['document']['document_name']}: "
            f"{result['stats']['node_count']} nodes, "
            f"{result['stats']['edge_count']} edges -> {result['export_path']}"
        )


if __name__ == "__main__":
    main()
