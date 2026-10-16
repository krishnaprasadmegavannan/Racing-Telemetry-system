import os, re, sys

def is_text_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            f.read(1024)
        return True
    except Exception:
        return False

root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.')
patterns = re.compile(r'(?i)secret|api[_-]?key|token|password|key|passwd')
extensions = {'.py', '.env', '.txt', '.json', '.yml', '.yaml'}
for dirpath, dirnames, filenames in os.walk(root):
    # skip .venv directories
    dirnames[:] = [d for d in dirnames if d != '.venv']
    for filename in filenames:
        if os.path.splitext(filename)[1] in extensions:
            full_path = os.path.join(dirpath, filename)
            if not is_text_file(full_path):
                continue
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f, 1):
                        if patterns.search(line):
                            print(f"{full_path}:{i}:{line.strip()}")
            except Exception as e:
                print(f"Error reading {full_path}: {e}", file=sys.stderr)
