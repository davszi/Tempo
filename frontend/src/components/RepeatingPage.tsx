import { useState } from "react";
import { practiceRequest, sideLabels, type ReviewStart, type Session } from "../lib/practiceApi";
import { PracticeSession } from "./PracticeSession";

export function RepeatingPage() {
  const [review, setReview] = useState<ReviewStart>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const pending = review?.status === "choose_side" ? review : undefined;

  async function request(action: () => Promise<ReviewStart>) {
    setBusy(true);
    setError("");
    try {
      setReview(await action());
    } catch (failure) {
      setError((failure as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (review?.status === "play") return <PracticeSession initial={review} learning={false} onExit={() => setReview(undefined)} />;

  return <div className="page">
    <header className="page-header"><div><h1>Repeating &amp; reviews</h1>
      <p>Practice the next opening line chosen by the review planner.</p></div></header>
    <section className="placeholder-card">
      {error && <p role="alert">{error}</p>}
      {pending ? <>
        <h2>{pending.name}</h2><p>Choose which side to play.</p>
        <div className="practice-controls">{pending.available_sides.map((side) =>
          <button key={side} className="primary-button" disabled={busy} onClick={() =>
            void request(() => practiceRequest<Session>("review/side", { session_id: pending.session_id, side }))
          }>{sideLabels[side]}</button>)}</div>
      </> : <>
        {review?.status === "learn_first" && <p role="status">Complete a Learning session to unlock your first review.</p>}
        {review?.status === "none_due" && <p role="status">You have no reviews due right now.</p>}
        <button className="primary-button" disabled={busy} onClick={() =>
          void request(() => practiceRequest<ReviewStart>("review"))
        }>{busy ? "Finding a review…" : "Start next review"}</button>
      </>}
    </section>
  </div>;
}
