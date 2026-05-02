from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_DIR))

from app.services import collect_articles


if __name__ == "__main__":
    saved_count = collect_articles()
    print(f"Saved {saved_count} new articles.")
