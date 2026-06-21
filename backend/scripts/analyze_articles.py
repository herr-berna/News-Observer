from pathlib import Path
import sys


BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_DIR))

from app.analysis import analyze_articles


if __name__ == "__main__":
    result = analyze_articles()
    print(
        "Analysis complete: "
        f"{result['normalized_articles']} normalized, "
        f"{result['duplicates']} duplicates, "
        f"{result['clusters']} clusters."
    )
