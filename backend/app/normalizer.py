import hashlib
import math
import os
import re
import unicodedata
from collections import Counter


from . import config  # noqa: F401


HASHING_EMBEDDING_DIMENSIONS = 384
HASHING_EMBEDDING_MODEL = "hashing-v2"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
OPENAI_EMBEDDING_DIMENSIONS = 1536

EMBEDDING_PROVIDER = os.getenv("NEWS_OBSERVER_EMBEDDING_PROVIDER", "auto")
EMBEDDING_MODEL = os.getenv("NEWS_OBSERVER_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
EMBEDDING_DIMENSIONS = int(
    os.getenv("NEWS_OBSERVER_EMBEDDING_DIMENSIONS", str(OPENAI_EMBEDDING_DIMENSIONS))
)

TOKEN_PATTERN = re.compile(r"[^\W_]+(?:['’-][^\W_]+)?", re.UNICODE)
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by",
    "for", "from", "has", "have", "he", "her", "his", "how", "in",
    "into", "is", "it", "its", "more", "new", "not", "of", "on", "or",
    "our", "said", "says", "she", "that", "the", "their", "they", "this",
    "to", "was", "were", "what", "when", "where", "which", "who", "why",
    "will", "with", "would", "you",
}


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = unicodedata.normalize("NFKC", value)
    value = value.replace("’", "'").replace("–", "-").replace("—", "-")
    return " ".join(value.split()).strip()


def tokenize(value: str | None) -> list[str]:
    normalized = normalize_text(value).casefold()
    return [
        token
        for token in TOKEN_PATTERN.findall(normalized)
        if len(token) > 2 and token not in STOP_WORDS
    ]


def content_fingerprint(title: str, text: str | None) -> str:
    content = f"{normalize_text(title).casefold()}\n{normalize_text(text).casefold()}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def extract_keywords(title: str, text: str | None, limit: int = 10) -> list[str]:
    title_tokens = tokenize(title)
    body_tokens = tokenize(text)
    scores = Counter(body_tokens)

    for token in title_tokens:
        scores[token] += 4

    return [
        token
        for token, _ in sorted(
            scores.items(),
            key=lambda item: (-item[1], item[0]),
        )[:limit]
    ]


def _feature_tokens(title: str, text: str | None) -> list[tuple[str, float]]:
    title_tokens = tokenize(title)
    body_tokens = tokenize(text)[:250]
    features = [(token, 5.0) for token in title_tokens]
    features.extend((token, 0.35) for token in body_tokens)
    features.extend(
        (f"{left}_{right}", 4.0)
        for left, right in zip(title_tokens, title_tokens[1:])
    )
    return features


def _semantic_input(title: str, text: str | None) -> str:
    title = normalize_text(title)
    text = normalize_text(text)
    if text:
        return f"Title: {title}\n\nArticle text: {text[:6000]}"
    return title or "untitled article"


def _selected_provider() -> str:
    provider = os.getenv(
        "NEWS_OBSERVER_EMBEDDING_PROVIDER",
        EMBEDDING_PROVIDER,
    ).strip().lower()
    if provider == "auto":
        return "openai" if os.getenv("OPENAI_API_KEY") else "hashing"
    return provider


def current_embedding_model() -> str:
    provider = _selected_provider()
    if provider == "openai":
        model = os.getenv("NEWS_OBSERVER_EMBEDDING_MODEL", EMBEDDING_MODEL)
        return f"openai:{model}"
    return HASHING_EMBEDDING_MODEL


def current_embedding_dimensions() -> int:
    if _selected_provider() == "openai":
        return int(
            os.getenv(
                "NEWS_OBSERVER_EMBEDDING_DIMENSIONS",
                str(EMBEDDING_DIMENSIONS),
            )
        )
    return int(
        os.getenv(
            "NEWS_OBSERVER_HASHING_EMBEDDING_DIMENSIONS",
            str(HASHING_EMBEDDING_DIMENSIONS),
        )
    )


def _create_hashing_embedding(
    title: str,
    text: str | None,
    dimensions: int | None = None,
) -> list[float]:
    dimensions = dimensions or current_embedding_dimensions()
    vector = [0.0] * dimensions

    for feature, weight in _feature_tokens(title, text):
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[index] += sign * weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm:
        vector = [value / norm for value in vector]

    return vector


def _create_openai_embeddings(inputs: list[str]) -> list[list[float]]:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "OpenAI embeddings require the `openai` package. "
            "Install backend requirements with `pip install -r requirements.txt`."
        ) from exc

    model = os.getenv("NEWS_OBSERVER_EMBEDDING_MODEL", EMBEDDING_MODEL)
    dimensions = os.getenv("NEWS_OBSERVER_EMBEDDING_DIMENSIONS")
    request = {
        "model": model,
        "input": inputs,
        "encoding_format": "float",
    }
    if dimensions:
        request["dimensions"] = int(dimensions)

    response = OpenAI().embeddings.create(**request)
    return [item.embedding for item in response.data]


def create_embedding(title: str, text: str | None) -> list[float]:
    if _selected_provider() == "openai":
        return _create_openai_embeddings([_semantic_input(title, text)])[0]
    return _create_hashing_embedding(title, text)


def create_embeddings(items: list[tuple[str, str | None]]) -> list[list[float]]:
    if not items:
        return []
    if _selected_provider() == "openai":
        return _create_openai_embeddings(
            [_semantic_input(title, text) for title, text in items]
        )
    return [_create_hashing_embedding(title, text) for title, text in items]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
