import sys
from pathlib import Path

def main():
    target = Path(sys.argv[1])
    target.parent.mkdir(parents=True, exist_ok=True)
    content = sys.stdin.read()
    target.write_text(content, encoding='utf-8')
    print(f"Wrote {len(content)} chars to {target}")

if __name__ == '__main__':
    main()
