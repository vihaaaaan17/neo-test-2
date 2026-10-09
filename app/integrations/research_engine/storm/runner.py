"""
Standalone STORM runner. Executed by `StormResearchEngine` in a SEPARATE Python environment.

Why a separate process: `knowledge-storm` pins `dspy_ai==2.4.9`, which requires `openai<2.0.0`, while the Neosis
application runs `openai>=2.45` (needed by `langchain-openai` 1.x / Open Deep Research). The two dependency sets cannot
share one environment, so STORM runs in its own virtualenv and this script is the only code that imports it.

This file must stay import-light and must NOT import anything from the `app` package. It only calls the real upstream
`STORMWikiRunner` (no STORM logic is reimplemented here) and reports through a tiny line protocol:

    stdin : one JSON job document
    stdout: lines prefixed with "@@NEOSIS@@" followed by a JSON event; everything else STORM prints is redirected to stderr

Events: {"type": "phase", "phase": "...", "message": "..."}  and finally one {"type": "result", ...} or {"type": "error", ...}.
"""
import json
import os
import re
import sys
import traceback

PREFIX = "@@NEOSIS@@"
_OUT = sys.stdout


def emit(event_type: str, **data) -> None:
    _OUT.write(PREFIX + json.dumps({"type": event_type, **data}) + "\n")
    _OUT.flush()


def safe_topic(topic: str) -> str:
    """
    STORM uses the topic text verbatim as an output directory name, so characters that are invalid in file names
    (notably `?` in a question such as "What is RAG?") crash it on Windows. Strip them; the meaning is unchanged.
    """
    cleaned = re.sub(r'[<>:"/\\|?*]', "", topic)
    cleaned = "".join(ch for ch in cleaned if ord(ch) >= 32).strip().rstrip(".")
    return cleaned or "research topic"


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    # Keep stdout clean for the protocol: anything STORM/dspy/tqdm prints goes to stderr.
    sys.stdout = sys.stderr

    job = json.load(sys.stdin)
    topic = safe_topic(job["topic"])
    output_dir = job["output_dir"]
    llm = job["llm"]
    args = job.get("args", {})

    from knowledge_storm import STORMWikiLMConfigs, STORMWikiRunner, STORMWikiRunnerArguments
    from knowledge_storm.lm import LitellmModel
    from knowledge_storm.rm import TavilySearchRM
    from knowledge_storm.storm_wiki.modules.callback import BaseCallbackHandler

    class Progress(BaseCallbackHandler):
        def on_identify_perspective_start(self, **kwargs):
            emit("phase", phase="planning", message="Identifying perspectives")

        def on_identify_perspective_end(self, perspectives=None, **kwargs):
            emit("phase", phase="planning", message=f"Identified {len(perspectives or [])} perspectives")

        def on_information_gathering_start(self, **kwargs):
            emit("phase", phase="executing", message="Researching via simulated expert conversations")

        def on_dialogue_turn_end(self, dlg_turn=None, **kwargs):
            emit("phase", phase="executing", message="Completed a research conversation turn")

        def on_information_gathering_end(self, **kwargs):
            emit("phase", phase="executing", message="Information gathering finished")

        def on_information_organization_start(self, **kwargs):
            emit("phase", phase="synthesizing", message="Organizing collected information")

        def on_direct_outline_generation_end(self, outline=None, **kwargs):
            emit("phase", phase="synthesizing", message="Draft outline generated")

        def on_outline_refinement_end(self, outline=None, **kwargs):
            emit("phase", phase="synthesizing", message="Outline refined; writing and polishing the article")

    # LLMs: STORM's own LitellmModel against the configured OpenAI-compatible endpoint. One model fills every STORM slot;
    # the per-slot token limits are STORM's own defaults (see STORMWikiLMConfigs.init_openai_model).
    model_name = llm["model"] if "/" in llm["model"] else f"openai/{llm['model']}"
    common = {"api_key": llm["api_key"], "temperature": 1.0, "top_p": 0.9}
    if llm.get("base_url"):
        common["api_base"] = llm["base_url"]

    def make_lm(max_tokens: int):
        return LitellmModel(model=model_name, max_tokens=max_tokens, **common)

    lm_configs = STORMWikiLMConfigs()
    lm_configs.set_conv_simulator_lm(make_lm(500))
    lm_configs.set_question_asker_lm(make_lm(500))
    lm_configs.set_outline_gen_lm(make_lm(400))
    lm_configs.set_article_gen_lm(make_lm(700))
    lm_configs.set_article_polish_lm(make_lm(4000))

    runner_args = STORMWikiRunnerArguments(
        output_dir=output_dir,
        max_conv_turn=int(args.get("max_conv_turn", 3)),
        max_perspective=int(args.get("max_perspective", 3)),
        max_search_queries_per_turn=int(args.get("max_search_queries_per_turn", 3)),
        search_top_k=int(args.get("search_top_k", 3)),
        retrieve_top_k=int(args.get("retrieve_top_k", 3)),
        max_thread_num=int(args.get("max_thread_num", 3)),
    )

    rm = TavilySearchRM(
        tavily_search_api_key=job["tavily_api_key"],
        k=runner_args.search_top_k,
        include_raw_content=True,
    )

    runner = STORMWikiRunner(runner_args, lm_configs, rm)
    emit("phase", phase="planning", message="Starting STORM")
    runner.run(
        topic=topic,
        do_research=True,
        do_generate_outline=True,
        do_generate_article=True,
        do_polish_article=True,
        remove_duplicate=False,
        callback_handler=Progress(),
    )

    # Collect token/call usage before post_run() resets it.
    usage = {"model_calls": 0, "input_tokens": 0, "output_tokens": 0}
    for slot in ("conv_simulator_lm", "question_asker_lm", "outline_gen_lm", "article_gen_lm", "article_polish_lm"):
        lm = getattr(lm_configs, slot, None)
        if lm is None:
            continue
        usage["model_calls"] += len(getattr(lm, "history", []) or [])
        for counts in lm.get_usage_and_reset().values():
            usage["input_tokens"] += counts.get("prompt_tokens", 0)
            usage["output_tokens"] += counts.get("completion_tokens", 0)
    runner.post_run()

    article_dir = runner.article_output_dir
    polished = os.path.join(article_dir, "storm_gen_article_polished.txt")
    with open(polished, "r", encoding="utf-8") as f:
        article = f.read()

    # url_to_info.json maps each cited URL to its unified citation index ([n] in the article) and its collected info.
    sources = []
    url_to_info_path = os.path.join(article_dir, "url_to_info.json")
    if os.path.exists(url_to_info_path):
        info = _read_json(url_to_info_path)
        index = info.get("url_to_unified_index", {})
        for url, details in info.get("url_to_info", {}).items():
            sources.append({
                "index": index.get(url),
                "url": url,
                "title": details.get("title"),
                "description": details.get("description"),
                "snippets": details.get("snippets", []),
            })

    emit("result", article=article, sources=sources, usage=usage, output_dir=article_dir)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # report any failure through the protocol, then exit non-zero
        emit("error", message=str(exc), traceback=traceback.format_exc())
        sys.exit(1)
