import { useState } from "react";
import { ArrowLeft, BookOpen, ChevronRight, Play } from "lucide-react";
import { useApp } from "../lib/app";
import { lineLabel } from "../lib/catalog";
import { dueAt, dueInfo, isDue, timeline } from "../lib/memory";
import { MemCard, fmtDate, plural } from "./common";

export function DashboardPage() {
  const { repertoire, progress, lineById, now, go, startReview, startLearning } = useApp();
  const lines = repertoire?.lines ?? [];
  const due = lines.filter((line) => isDue(line, now));
  const next = lines.filter((line) => !isDue(line, now)).sort((a, b) => dueAt(a) - dueAt(b))[0];
  const inProgress = Object.entries(progress).map(([id, saved]) => ({ line: lineById.get(Number(id)), saved }))
    .filter((item) => item.line).sort((a, b) => b.saved.at - a.saved.at);
  const hour = new Date(now).getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
  const target = repertoire?.target_recall ?? 0.9;

  const reviewCard = due.length
    ? <div className="card hero"><p className="eyebrow" style={{ color: "inherit", opacity: 0.8 }}>REPEATING</p><h2>{plural(due.length, "line")} ready for review</h2>
      <p>Recall them without hints. TEMPO grades each one and plans its next review.</p>
      <button className="btn" onClick={() => void startReview()}><Play size={16} /> Start review</button></div>
    : lines.length && next
      ? <div className="card"><p className="eyebrow">REPEATING</p><h2>All caught up</h2>
        <p className="muted">Next review: <b>{lineLabel(next)}</b>, {dueInfo(next, now, target).long.toLowerCase()}</p>
        <button className="btn ghost" onClick={() => go("#/review")}>Open the queue</button></div>
      : <div className="card"><p className="eyebrow">REPEATING</p><h2>Nothing to review yet</h2>
        <p className="muted">Learn your first opening line. It joins your repertoire, and its first recall test is ready straight away.</p>
        <button className="btn primary" onClick={() => go("#/learn")}><BookOpen size={16} /> Browse openings</button></div>;

  return <>
    <header className="page-head"><p className="eyebrow">YOUR LEARNING SPACE</p><h1>{greeting}.</h1>
      <p className="lead">{due.length ? `You have ${plural(due.length, "line")} to review today.` : lines.length ? "Your repertoire is fresh. Learn something new?" : "Pick an opening, learn one line, and TEMPO will remind you before you forget it."}</p></header>
    <div className="grid2">{reviewCard}
      <div className="card"><div className="row" style={{ marginBottom: 14 }}><h2>Continue learning</h2><span className="spacer" />
        <button className="btn sm ghost" onClick={() => go("#/learn")}>All openings</button></div>
        {inProgress.length ? <ul className="list">{inProgress.slice(0, 4).map(({ line, saved }) => <li key={line!.line_id}>
          <button className="item" onClick={() => void startLearning(line!.line_id)}>
            <span className="grow"><b>{line!.opening_family} · {lineLabel(line!)}</b><small>Playing {saved.side === "black" ? "Black" : "White"} · {saved.ply} of {saved.total} half-moves</small>
              <span className="bar" style={{ marginTop: 6 }}><i style={{ width: `${Math.round(saved.ply / saved.total * 100)}%` }} /></span></span>
            <ChevronRight size={18} /></button></li>)}</ul>
          : <div className="empty">Nothing in progress. Leave a lesson at any time and it waits for you here.</div>}
      </div>
    </div>
    <MemoryTimeline />
  </>;
}

/** The 30-day review schedule (OPEN.md product to-do 4) and the lines fading soonest, in one card. */
function MemoryTimeline() {
  const { repertoire, now, go } = useApp();
  const [picked, setPicked] = useState<number | null>(null);
  const lines = repertoire?.lines ?? [];
  const target = Math.round((repertoire?.target_recall ?? 0.9) * 100);
  const { days, later } = timeline(lines, now);
  const max = Math.max(4, ...days.map((day) => day.lines.length));
  const week = days.slice(1, 7).reduce((sum, day) => sum + day.lines.length, 0);
  const selected = picked == null ? null : days.find((day) => day.day === picked) ?? null;
  const shown = selected ? selected.lines.map((i) => lines[i]) : [...lines].sort((a, b) => dueAt(a) - dueAt(b)).slice(0, 6);

  const strip = <div className="tl-wrap"><div className="tl">{days.map((day) => {
    const count = day.lines.length, onTime = count - day.late, weekday = new Date(day.day).getDay();
    const label = day.index === 0 ? "Today" : weekday === 1 ? fmtDate(day.day, { day: "numeric", month: "short" }) : "";
    return <button key={day.day} className={`tl-day ${day.index === 0 ? "today" : ""} ${selected?.day === day.day ? "on" : ""} ${weekday === 0 || weekday === 6 ? "we" : ""}`}
      title={`${day.index === 0 ? "Today" : fmtDate(day.day)}: ${plural(count, "line")}${day.late ? `, ${day.late} overdue` : ""}`}
      tabIndex={lines.length ? 0 : -1} onClick={() => setPicked(selected?.day === day.day ? null : day.day)}>
      <span className="tl-n">{count || ""}</span>
      <span className="tl-bar">{count ? <>{day.late > 0 && <i className="late" style={{ height: `${day.late / max * 100}%` }} />}
        {onTime > 0 && <i style={{ height: `${onTime / max * 100}%` }} />}</> : <i className="zero" />}</span>
      <small>{label}</small></button>;
  })}</div></div>;
  const summary = lines.length > 0 && <div className="mem-sum"><span><b>{days[0].lines.length}</b> today</span><span><b>{week}</b> rest of the week</span>
    <span><b>{lines.length - days[0].lines.length - week - later}</b> later this month</span>{later > 0 && <span><b>{later}</b> after 30 days</span>}</div>;
  const head = <div className="mem-head"><div><p className="eyebrow">MEMORY TIMELINE</p><h2>When each line starts to fade</h2>
    <p>Each line sits on the day its predicted recall drops below {target}%, which is when TEMPO brings it back.</p></div>{summary}</div>;

  if (!lines.length) {
    return <section className="card mem mem-empty">{head}{strip}
      <div className="empty"><h3>Your timeline is empty</h3>Learn a line and it lands here on the day you're likely to start forgetting it.<br />
        <button className="btn primary" onClick={() => go("#/learn")}><BookOpen size={16} /> Learn your first line</button></div></section>;
  }
  return <section className="card mem">{head}{strip}
    <div className="mem-list-head"><h3>{selected ? (selected.index === 0 ? "Today" : fmtDate(selected.day, { weekday: "long", day: "numeric", month: "long" })) : "Fading soonest"}</h3>
      <span className="chip plain">{plural(shown.length, "line")}</span><span className="spacer" />
      {selected ? <button className="btn sm ghost" onClick={() => setPicked(null)}><ArrowLeft size={14} /> Fading soonest</button>
        : <span className="muted small">Tap a day to see its lines</span>}</div>
    {shown.length ? <div className="mgrid">{shown.map((line) => <MemCard key={line.line_id} line={line} />)}</div> : <div className="empty">No reviews on this day.</div>}
  </section>;
}
