function formatDate(value) {
  if (!value) {
    return "Date unavailable";
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}


export default function EventCard({ event, selected, onSelect }) {
  const sourceCount = event.sources.length;

  return (
    <button
      className={`event-card ${selected ? "selected" : ""}`}
      onClick={() => onSelect(event)}
      type="button"
    >
      <div className="event-card-topline">
        <span className={`coverage-dot ${sourceCount > 1 ? "compared" : ""}`} />
        <span>
          {sourceCount > 1 ? `${sourceCount} sources` : "Single source"}
        </span>
        <time>{formatDate(event.ended_at)}</time>
      </div>

      <h2>{event.label}</h2>

      <div className="source-row">
        {event.sources.map((source) => (
          <span className="source-chip" key={source}>
            {source}
          </span>
        ))}
      </div>

      <p className="article-count">
        {event.article_count} {event.article_count === 1 ? "article" : "articles"}
      </p>
    </button>
  );
}
