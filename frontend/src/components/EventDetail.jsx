import CoverageCard from "./CoverageCard";


function formatDateRange(start, end) {
  if (!start && !end) {
    return "Date unavailable";
  }

  const formatter = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  const startDate = start ? formatter.format(new Date(start)) : null;
  const endDate = end ? formatter.format(new Date(end)) : null;

  return startDate === endDate || !startDate
    ? endDate
    : `${startDate} – ${endDate}`;
}


export default function EventDetail({ event, loading, error }) {
  if (loading) {
    return (
      <div className="detail-state">
        <span className="loader" />
        <p>Loading event coverage…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="detail-state error">
        <h2>Could not load this event</h2>
        <p>{error}</p>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="detail-state">
        <p className="eyebrow">Event explorer</p>
        <h2>Select an event</h2>
        <p>
          Choose a grouped story to compare how each outlet covers the same
          event.
        </p>
      </div>
    );
  }

  return (
    <div className="event-detail-content">
      <header className="event-heading">
        <p className="eyebrow">Observed event</p>
        <h1>{event.label}</h1>

        <div className="event-facts">
          <span>{formatDateRange(event.started_at, event.ended_at)}</span>
          <span>{event.article_count} articles</span>
          <span>{event.sources.length} sources</span>
        </div>

        {event.keywords.length > 0 && (
          <div className="keyword-row" aria-label="Event keywords">
            {event.keywords.map((keyword) => (
              <span key={keyword}>{keyword}</span>
            ))}
          </div>
        )}
      </header>

      <section className="summary-panel">
        <div>
          <p className="eyebrow">Neutral summary</p>
          <h2>What happened</h2>
        </div>
        <p>
          {event.summary ||
            "AI-generated summaries are not enabled yet. The source coverage below is grouped by the clustering pipeline."}
        </p>
      </section>

      <section className="coverage-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Source comparison</p>
            <h2>Coverage</h2>
          </div>
          <p>
            {event.sources.length > 1
              ? `${event.sources.length} outlets reporting this event`
              : "Currently reported by one outlet"}
          </p>
        </div>

        <div className="coverage-grid">
          {event.articles.map((article) => (
            <CoverageCard article={article} key={article.id} />
          ))}
        </div>
      </section>
    </div>
  );
}
