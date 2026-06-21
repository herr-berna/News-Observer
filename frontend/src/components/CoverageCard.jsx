function formatDate(value) {
  if (!value) {
    return "Date unavailable";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


function excerpt(text) {
  if (!text) {
    return "No extracted article text is available.";
  }

  const normalized = text.replace(/\s+/g, " ").trim();
  return normalized.length > 360
    ? `${normalized.slice(0, 360)}…`
    : normalized;
}


export default function CoverageCard({ article }) {
  return (
    <article className="coverage-card">
      <div className="coverage-source">
        <span>{article.source}</span>
        {article.country && <span className="country-code">{article.country}</span>}
      </div>

      <h3>{article.title}</h3>

      <div className="coverage-meta">
        <time>{formatDate(article.published_at || article.collected_at)}</time>
        {article.author && <span>By {article.author}</span>}
        {article.category && <span>{article.category}</span>}
      </div>

      <p>{excerpt(article.text)}</p>

      <a href={article.url} rel="noreferrer" target="_blank">
        Read original <span aria-hidden="true">↗</span>
      </a>
    </article>
  );
}
