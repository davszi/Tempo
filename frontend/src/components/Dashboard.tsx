import { BookOpen, Clock3, ChevronRight, RotateCcw } from "lucide-react";
import type { Opening, UserProgress } from "../types";
import { todayISO } from "../lib/dates";
import { UpcomingReviews } from "./UpcomingReviews";
export function Dashboard({
  username,
  progress,
  onLearn,
  onReview,
  onPlanner,
  openings,
}: {
  username: string;
  progress: UserProgress;
  onLearn: () => void;
  onReview: () => void;
  onPlanner: () => void;
  openings: Opening[];
}) {
  const learned = openings.filter((opening) => progress[opening.id]?.status === "completed").length;
  const due = Object.values(progress).filter(
    (item) => item.nextReview && item.nextReview <= todayISO(),
  ).length;
  return (
    <div className="page dashboard-page">
      <header className="page-header welcome-header">
        <div>
          <p className="eyebrow">YOUR LEARNING SPACE</p>
          <h1>Welcome back, {username}.</h1>
          <p>Ready for a few focused moves?</p>
        </div>
        <div className="header-knight" aria-hidden="true">
          ♞
        </div>
      </header>
      <section className="stat-grid">
        <article className="stat-card">
          <span className="stat-icon">
            <BookOpen />
          </span>
          <div>
            <strong>{learned}</strong>
            <p>Opening lines learned</p>
          </div>
          <span className="stat-total">of {openings.length}</span>
        </article>
        <article className="stat-card">
          <span className="stat-icon">
            <Clock3 />
          </span>
          <div>
            <strong>{due}</strong>
            <p>Reviews due today</p>
          </div>
          <span className="stat-total">{due ? "Ready" : "All clear"}</span>
        </article>
      </section>
      <section className="action-grid">
        <button className="action-card primary-action" onClick={onLearn}>
          <span className="action-icon">
            <BookOpen />
          </span>
          <span>
            <b>Start learning</b>
            <small>Explore a new opening line</small>
          </span>
          <ChevronRight />
        </button>
        <button className="action-card" onClick={onReview}>
          <span className="action-icon">
            <RotateCcw />
          </span>
          <span>
            <b>Start review</b>
            <small>Strengthen what you know</small>
          </span>
          <ChevronRight />
        </button>
      </section>
      <div className="dashboard-insights">
        <UpcomingReviews progress={progress} onOpen={onPlanner} />
      </div>
    </div>
  );
}
