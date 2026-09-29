import os
import ast

versions_dir = 'alembic/versions'
files = [f for f in os.listdir(versions_dir) if f.endswith('.py') and not f.startswith('__')]
revs = {}

for f in files:
    filepath = os.path.join(versions_dir, f)
    with open(filepath, 'r', encoding='utf-8') as fp:
        tree = ast.parse(fp.read(), filename=filepath)
    
    rev = None
    down = None
    has_upgrade = False
    has_downgrade = False

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == 'revision':
                        if isinstance(node.value, ast.Constant):
                            rev = node.value.value
                    elif target.id == 'down_revision':
                        if isinstance(node.value, ast.Constant):
                            down = node.value.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                if node.target.id == 'revision':
                    if isinstance(node.value, ast.Constant):
                        rev = node.value.value
                elif node.target.id == 'down_revision':
                    if isinstance(node.value, ast.Constant):
                        down = node.value.value
        elif isinstance(node, ast.FunctionDef):
            if node.name == 'upgrade':
                has_upgrade = len(node.body) > 0 and not (len(node.body) == 1 and isinstance(node.body[0], ast.Pass))
            elif node.name == 'downgrade':
                has_downgrade = len(node.body) > 0 and not (len(node.body) == 1 and isinstance(node.body[0], ast.Pass))

    revs[rev] = {
        'file': f,
        'down': down,
        'has_upgrade': has_upgrade,
        'has_downgrade': has_downgrade,
    }

print(f"Total revisions parsed: {len(revs)}")
for rev, data in revs.items():
    print(f"rev: {rev} -> down: {data['down']} | up: {data['has_upgrade']}, down_fn: {data['has_downgrade']} ({data['file']})")

roots = [r for r, d in revs.items() if d['down'] is None]
print(f"\nRoots: {roots}")

down_to_rev = {}
for r, d in revs.items():
    if d['down'] is not None:
        down_to_rev[d['down']] = r

if len(roots) == 1:
    curr = roots[0]
    chain = [curr]
    while curr in down_to_rev:
        curr = down_to_rev[curr]
        chain.append(curr)
    print(f"Chain length: {len(chain)} / {len(revs)}")
    if len(chain) == len(revs):
        print(f"PERFECT LINEAR DAG! Head is {curr}")
    else:
        missing = set(revs.keys()) - set(chain)
        print(f"Missing from chain: {missing}")
else:
    print(f"Error: multiple roots or no roots: {roots}")
