import { CalendarDays, ChevronRight } from "lucide-react";
import type { UserProgress } from "../types";
import { todayISO } from "../lib/dates";
export function UpcomingReviews({ progress, onOpen }: { progress: UserProgress; onOpen: () => void }) {
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date();
    date.setDate(date.getDate() + index);
    const iso = todayISO(date);
    const reviews = Object.values(progress).filter((item) => item.nextReview === iso).length;
    return {
      iso,
      reviews,
      weekday: new Intl.DateTimeFormat("en", { weekday: "short" }).format(date),
      date: new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(date),
    };
  });

  return (
    <section className="upcoming-card">
      <div className="upcoming-heading">
        <span className="insight-title-icon">
          <CalendarDays size={21} />
        </span>
        <div>
          <h2>Upcoming reviews</h2>
          <p>Your scheduled practice plan</p>
        </div>
        <button className="upcoming-link" type="button" onClick={onOpen}>
          Open review planner <ChevronRight size={16} />
        </button>
      </div>
      <div className="upcoming-days">
        {days.map((day, index) => (
          <button
            type="button"
            key={day.iso}
            className={index === 0 ? "today" : ""}
            onClick={onOpen}
            aria-label={`${day.weekday}, ${day.date}: ${day.reviews} reviews`}
          >
            <b>{day.weekday}</b>
            <span>{day.date}</span>
            <strong>{day.reviews}</strong>
            <small>{day.reviews === 1 ? "review" : "reviews"}</small>
          </button>
        ))}
      </div>
    </section>
  );
}
