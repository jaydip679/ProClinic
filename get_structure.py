import ast
import os
import glob

def parse_file(filepath):
    try:
        with open(filepath, "r") as f:
            tree = ast.parse(f.read(), filename=filepath)
    except Exception as e:
        return f"Error parsing {filepath}: {e}\n"

    output = []
    output.append(f"--- {filepath} ---")
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            bases_str = f"({', '.join(bases)})" if bases else ""
            output.append(f"class {node.name}{bases_str}:")
            for subnode in node.body:
                if isinstance(subnode, ast.FunctionDef):
                    output.append(f"    def {subnode.name}(...):")
        elif isinstance(node, ast.FunctionDef):
            output.append(f"def {node.name}(...):")
    return "\n".join(output) + "\n\n"

with open("codebase_structure.txt", "w") as out:
    for filepath in glob.glob("backend/**/*.py", recursive=True):
        if 'migrations' in filepath or '__pycache__' in filepath: continue
        out.write(parse_file(filepath))
