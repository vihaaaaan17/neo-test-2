import sys, json
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.export import to_json, to_html
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding="utf-8"))
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding="utf-8"))
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding="utf-8"))

G = build_from_json(extraction, root='app', directed=False)
communities = {int(k): v for k, v in analysis['communities'].items()}
labels = json.loads(Path('graphify-out/.graphify_labels.json').read_text(encoding="utf-8"))
labels = {int(k): v for k, v in labels.items()}

to_json(G, communities, 'graphify-out/graph.json', community_labels=labels, force=True)
to_html('graphify-out/graph.json', 'graphify-out/graph.html')
print("HTML generated successfully at graphify-out/graph.html")
