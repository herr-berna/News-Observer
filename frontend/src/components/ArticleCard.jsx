function formatDate(value) {
  if (!value) {
    return "Unknown date";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


export default function ArticleCard({ article, selected, onSelect }) {
  const preview = article.text
    ? `${article.text.slice(0, 200)}${article.text.length > 200 ? "..." : ""}`
    : "No extracted text available yet.";

  return (
    <button
      className={`article-card ${selected ? "selected" : ""}`}
      onClick={() => onSelect(article)}
      type="button"
    >
      <div className="article-meta">
        <span>{article.source}</span>
        <span>{formatDate(article.published_at || article.collected_at)}</span>
      </div>
      <h2>{article.title}</h2>
      <p>{preview}</p>
    </button>
  );
}
