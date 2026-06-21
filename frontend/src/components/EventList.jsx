import EventCard from "./EventCard";


export default function EventList({ events, selectedId, onSelect }) {
  if (events.length === 0) {
    return (
      <div className="list-empty">
        <p>No events match these filters.</p>
      </div>
    );
  }

  return (
    <div className="event-list">
      {events.map((event) => (
        <EventCard
          event={event}
          key={event.id}
          onSelect={onSelect}
          selected={selectedId === event.id}
        />
      ))}
    </div>
  );
}
