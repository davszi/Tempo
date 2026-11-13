import { BookOpen, ChevronRight, RotateCcw } from "lucide-react";
export function Dashboard({
  username,
  onLearn,
  onReview,
}: {
  username: string;
  onLearn: () => void;
  onReview: () => void;
}) {
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
    </div>
  );
}
