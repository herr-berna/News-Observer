import requests
import trafilatura


def _fix_mojibake(text: str | None) -> str | None:
    if not text or ("â" not in text and "Â" not in text):
        return text

    try:
        fixed = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text

    return fixed if fixed.count("â") + fixed.count("Â") < text.count("â") + text.count("Â") else text


def extract_article_text(url: str) -> str | None:
    response = requests.get(
        url,
        timeout=15,
        headers={"User-Agent": "NewsObserver/1.0"},
    )
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding

    return _fix_mojibake(trafilatura.extract(response.text))
