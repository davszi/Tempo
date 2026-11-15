import { BookOpen, Play } from "lucide-react";
import { useApp } from "../lib/app";
import { dayDiff, dayStart, dueAt, isDue } from "../lib/memory";
import type { RepertoireLine } from "../lib/practiceApi";
import { MemRow, fmtDate, plural } from "./common";

/** Repeating mode: the review queue and what comes up next, as one timeline from now into the coming days. */
export function ReviewPage() {
  const { repertoire, now, go, startReview } = useApp();
  const lines = repertoire?.lines ?? [];
  const head = <header className="page-head"><p className="eyebrow">REPEATING MODE</p><h1>Recall without hints.</h1>
    <p className="lead">Play your side from memory. The first mistake shows the move once; a second one lets you re-learn the line or carry on.</p></header>;
  if (!repertoire) return <>{head}<div className="empty">Loading your repertoire…</div></>;
  if (!lines.length) return <>{head}<div className="empty"><h3>Your repertoire is empty</h3>Lines appear here automatically after you learn them.<br />
    <button className="btn primary" onClick={() => go("#/learn")}><BookOpen size={16} /> Learn your first line</button></div></>;

  const due = lines.filter((line) => isDue(line, now)).sort((a, b) => dueAt(a) - dueAt(b));
  const groups: { day: number; lines: RepertoireLine[] }[] = [];
  lines.filter((line) => !isDue(line, now)).sort((a, b) => dueAt(a) - dueAt(b)).forEach((line) => {
    const day = dayStart(dueAt(line));
    const group = groups.find((item) => item.day === day);
    if (group) group.lines.push(line); else groups.push({ day, lines: [line] });
  });
  const shown = groups.slice(0, 6), rest = groups.slice(6).reduce((sum, group) => sum + group.lines.length, 0);
  const when = (day: number) => { const days = dayDiff(day, now); return days <= 0 ? "Later today" : days === 1 ? "Tomorrow" : `In ${days} days`; };

  return <>{head}<section className="card queue" aria-label="Review queue">
    {due.length ? <div className="q-node now"><span className="q-dot" />
      <div className="q-when"><h2>Now</h2><span>{plural(due.length, "line")} ready · most overdue first</span><span className="spacer" />
        <button className="btn primary" onClick={() => void startReview()}><Play size={16} /> Start review</button></div>
      {due.map((line) => <MemRow key={line.line_id} line={line} />)}</div>
      : <div className="q-node now idle"><span className="q-dot" />
        <div className="q-when"><h2>Now</h2><span>Nothing is due. You're all caught up.</span></div>
        <p className="muted small" style={{ margin: 0 }}>Want to practise anyway? Pick any line below. It is graded and rescheduled the same way.</p></div>}
    {shown.map((group) => <div className="q-node later" key={group.day}><span className="q-dot" />
      <div className="q-when"><h2>{when(group.day)}</h2><span>{fmtDate(group.day, { weekday: "long", day: "numeric", month: "short" })} · {plural(group.lines.length, "line")}</span></div>
      {group.lines.map((line) => <MemRow key={line.line_id} line={line} />)}</div>)}
    {rest > 0 && <div className="q-node idle"><span className="q-dot" /><div className="q-when"><h2>Later</h2><span>{plural(rest, "more line")} after that</span></div></div>}
  </section></>;
}
