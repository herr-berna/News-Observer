import { useEffect, useMemo, useState } from "react";

import { fetchCluster, fetchClusters } from "./api";
import EventDetail from "./components/EventDetail";
import EventList from "./components/EventList";
import "./dashboard.css";


export default function App() {
  const [events, setEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("all");
  const [comparisonOnly, setComparisonOnly] = useState(true);
  const [loadingEvents, setLoadingEvents] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [listError, setListError] = useState("");
  const [detailError, setDetailError] = useState("");

  useEffect(() => {
    fetchClusters()
      .then((data) => {
        setEvents(data);
        const firstComparison =
          data.find((event) => event.sources.length > 1) || data[0];
        if (firstComparison) {
          setSelectedEventId(firstComparison.id);
        }
      })
      .catch((error) => setListError(error.message))
      .finally(() => setLoadingEvents(false));
  }, []);

  useEffect(() => {
    if (!selectedEventId) {
      setSelectedEvent(null);
      return;
    }

    let active = true;
    setLoadingDetail(true);
    setDetailError("");

    fetchCluster(selectedEventId)
      .then((data) => {
        if (active) {
          setSelectedEvent(data);
        }
      })
      .catch((error) => {
        if (active) {
          setDetailError(error.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoadingDetail(false);
        }
      });

    return () => {
      active = false;
    };
  }, [selectedEventId]);

  const sources = useMemo(
    () =>
      [...new Set(events.flatMap((event) => event.sources))].sort((a, b) =>
        a.localeCompare(b),
      ),
    [events],
  );

  const filteredEvents = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();

    return events.filter((event) => {
      const matchesSearch =
        !query ||
        event.label.toLocaleLowerCase().includes(query) ||
        event.keywords.some((keyword) =>
          keyword.toLocaleLowerCase().includes(query),
        );
      const matchesSource =
        sourceFilter === "all" || event.sources.includes(sourceFilter);
      const matchesComparison =
        !comparisonOnly || event.sources.length > 1;

      return matchesSearch && matchesSource && matchesComparison;
    });
  }, [comparisonOnly, events, search, sourceFilter]);

  const comparisonCount = events.filter(
    (event) => event.sources.length > 1,
  ).length;

  return (
    <main className="dashboard">
      <aside className="event-sidebar">
        <header className="brand">
          <div className="brand-mark" aria-hidden="true">
            NO
          </div>
          <div>
            <p>NewsObserver</p>
            <span>Event intelligence</span>
          </div>
        </header>

        <section className="sidebar-intro">
          <p className="eyebrow">Live dataset</p>
          <h1>News events</h1>
          <p>
            Articles grouped by topic similarity, publication time and source.
          </p>
        </section>

        <div className="dataset-stats">
          <div>
            <strong>{events.length}</strong>
            <span>events</span>
          </div>
          <div>
            <strong>{comparisonCount}</strong>
            <span>compared</span>
          </div>
          <div>
            <strong>{sources.length}</strong>
            <span>sources</span>
          </div>
        </div>

        <div className="filters">
          <label className="search-field">
            <span className="sr-only">Search events</span>
            <span aria-hidden="true">⌕</span>
            <input
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search events or keywords"
              type="search"
              value={search}
            />
          </label>

          <div className="filter-row">
            <label>
              <span className="sr-only">Filter by source</span>
              <select
                onChange={(event) => setSourceFilter(event.target.value)}
                value={sourceFilter}
              >
                <option value="all">All sources</option>
                {sources.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </select>
            </label>

            <label className="comparison-toggle">
              <input
                checked={comparisonOnly}
                onChange={(event) => setComparisonOnly(event.target.checked)}
                type="checkbox"
              />
              <span>Multi-source only</span>
            </label>
          </div>
        </div>

        <div className="event-list-shell">
          <div className="list-label">
            <span>{filteredEvents.length} results</span>
            <span>Newest first</span>
          </div>

          {loadingEvents && <p className="status">Loading events…</p>}
          {listError && (
            <p className="status error">Could not load events: {listError}</p>
          )}
          {!loadingEvents && !listError && (
            <EventList
              events={filteredEvents}
              onSelect={(event) => setSelectedEventId(event.id)}
              selectedId={selectedEventId}
            />
          )}
        </div>
      </aside>

      <section className="event-detail">
        <EventDetail
          error={detailError}
          event={selectedEvent}
          loading={loadingDetail}
        />
      </section>
    </main>
  );
}
