import sys, json
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json, to_html
from graphify.detect import save_manifest
from graphify.cli import _stamped_manifest_files
from pathlib import Path
from datetime import datetime, timezone

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding="utf-8"))
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding="utf-8"))
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding="utf-8"))

G = build_from_json(extraction, root='app', directed=False)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': 0, 'output': 0}

# Generate meaningful labels based on node names in each community
labels = {}
for cid, nodes in communities.items():
    node_names = [G.nodes[n].get('label', n) for n in nodes[:5]]
    sample = ", ".join(node_names)
    if any("Research" in n or "retriever" in n.lower() for n in node_names):
        labels[cid] = f"Research Fabric & Retrievers ({cid})"
    elif any("worker" in n.lower() or "task" in n.lower() or "job" in n.lower() for n in node_names):
        labels[cid] = f"Worker Tasks & Queues ({cid})"
    elif any("open_notebook" in n.lower() or "ground" in n.lower() for n in node_names):
        labels[cid] = f"Ground & Open Notebook ({cid})"
    elif any("model" in n.lower() or "schema" in n.lower() or "workspace" in n.lower() for n in node_names):
        labels[cid] = f"Data Models & Schema ({cid})"
    elif any("route" in n.lower() or "api" in n.lower() or "endpoint" in n.lower() for n in node_names):
        labels[cid] = f"API Routes & Endpoints ({cid})"
    elif any("config" in n.lower() or "setting" in n.lower() or "database" in n.lower() for n in node_names):
        labels[cid] = f"Core Configuration & DB ({cid})"
    else:
        labels[cid] = f"Module Group {cid}"

questions = suggest_questions(G, communities, labels)
report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, 'app', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding="utf-8")
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding="utf-8")

to_json(G, communities, 'graphify-out/graph.json', community_labels=labels, force=True)
to_html('graphify-out/graph.json', 'graphify-out/graph.html')

# Save manifest
_corpus = detection.get('all_files') or detection['files']
_manifest_files = _stamped_manifest_files(_corpus, extraction, Path('app'))
_scan = {f for fl in _corpus.values() for f in fl}
save_manifest(_manifest_files, root='app', scan_corpus=_scan)

print("Export completed: HTML, JSON, and Report successfully written.")
