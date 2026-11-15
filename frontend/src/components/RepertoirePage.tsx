import { useState } from "react";
import { BookOpen, Play, RotateCcw, Search } from "lucide-react";
import { useApp } from "../lib/app";
import { lineLabel } from "../lib/catalog";
import { DAY, dueInfo, isDue } from "../lib/memory";
import { positionAt } from "../lib/learning";
import type { OpeningLine, RepertoireLine } from "../lib/practiceApi";
import type { LessonProgress } from "../lib/progress";
import { ChessBoard } from "./ChessBoard";
import { DueChip, LineTitle, Meter, MoveChips, fmtDate, plural, recallText, sideName } from "./common";

const TABS = [
  ["all", "All lines", "", "Every line you've learned, most urgent first."],
  ["due", "Review now", "var(--again)", "Your recall of these has dropped to your target. A quick review resets them."],
  ["fresh", "Fresh", "var(--good)", "Remembered well. TEMPO brings each one back before it fades."],
  ["learning", "Still learning", "var(--hard)", "Lessons you started but haven't finished. They join your repertoire when you finish."],
] as const;
type Tab = typeof TABS[number][0];
type Item = { key: string; rep?: RepertoireLine; lesson?: { line: OpeningLine; saved: LessonProgress } };
const gradeClass = { Again: "g1", Hard: "g2", Good: "g3", Easy: "g4" } as const;

/** The repertoire (OPEN.md product to-do 5): status tabs, a search, one card per line, and a detail panel. */
export function RepertoirePage() {
  const { repertoire, progress, lineById, now, go } = useApp();
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");
  const [side, setSide] = useState<"all" | "white" | "black">("all");
  const [picked, setPicked] = useState<string | null>(null);
  const head = <header className="page-head"><p className="eyebrow">REPERTOIRE</p><h1>Your openings, at a glance.</h1>
    <p className="lead">The bar under each line is your memory of it: long and green means fresh, short and red means it's fading. Pick a line to see its moves and history.</p></header>;
  const lines = repertoire?.lines ?? [];
  const lessons = Object.entries(progress).map(([id, saved]) => ({ line: lineById.get(Number(id)), saved }))
    .filter((item): item is { line: OpeningLine; saved: LessonProgress } => !!item.line).sort((a, b) => b.saved.at - a.saved.at);
  if (!repertoire) return <>{head}<div className="empty">Loading your repertoire…</div></>;
  if (!lines.length && !lessons.length) {
    return <>{head}<div className="card"><div className="steps">
      <div><span className="step-n">1</span><b>Learn a line</b><small>Follow the arrows in Learning mode.</small></div>
      <div><span className="step-n">2</span><b>It lands here</b><small>With a memory bar that slowly drains.</small></div>
      <div><span className="step-n">3</span><b>Review in time</b><small>TEMPO calls it back before you forget.</small></div></div>
      <div style={{ textAlign: "center", marginTop: 18 }}><button className="btn primary" onClick={() => go("#/learn")}><BookOpen size={16} /> Learn your first line</button></div></div></>;
  }

  const term = query.trim().toLowerCase();
  const matches = (line: { name: string; opening_family: string; eco: string; family_side: string }) =>
    (!term || `${line.opening_family} ${line.name} ${line.eco}`.toLowerCase().includes(term)) && (side === "all" || line.family_side === side);
  const counts = { all: lines.length, due: lines.filter((l) => isDue(l, now)).length, fresh: lines.filter((l) => !isDue(l, now)).length, learning: lessons.length };
  const items: Item[] = tab === "learning"
    ? lessons.filter((lesson) => matches(lesson.line)).map((lesson) => ({ key: `p${lesson.line.line_id}`, lesson }))
    : lines.filter((line) => (tab === "all" || (tab === "due") === isDue(line, now)) && matches(line)).map((rep) => ({ key: `r${rep.line_id}`, rep }));
  const narrow = typeof window !== "undefined" && window.innerWidth <= 1100;   // small screens open the detail only on request
  const selected = items.find((item) => item.key === picked) ?? (narrow ? undefined : items[0]);
  const current = TABS.find((item) => item[0] === tab)!;

  function pick(key: string) {
    setPicked(key);
    if (window.innerWidth <= 1100) requestAnimationFrame(() => document.querySelector(".detail")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  return <>{head}
    <div className="seg" role="tablist" aria-label="Filter by status">{TABS.map(([id, label, dot]) =>
      <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? "on" : ""} onClick={() => { setTab(id); setPicked(null); }}>
        {dot && <span className="dot" style={{ background: dot }} />}{label}<span className="n">{counts[id]}</span></button>)}</div>
    <p className="tab-help">{current[3]}</p>
    <div className="controls">
      <label className="search"><Search size={18} /><span className="sr">Search your lines</span>
        <input type="search" placeholder="Search by opening, variation or ECO" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /></label>
      <div className="chips">{([["all", "All sides"], ["white", "White"], ["black", "Black"]] as const).map(([value, label]) =>
        <button key={value} className={`fchip ${side === value ? "on" : ""}`} onClick={() => setSide(value)}>{label}</button>)}</div>
    </div>
    {items.length ? <div className="split rep-split"><div className="rep-grid">{items.map((item) => <RepCard key={item.key} item={item} on={selected?.key === item.key} onPick={() => pick(item.key)} />)}</div>
      {selected && <Detail item={selected} />}</div>
      : <div className="empty">{tab === "due" && !term ? "Nothing needs a review right now. Nice." : tab === "learning" && !term ? "No unfinished lessons." : "No line matches."}</div>}
  </>;
}

function RepCard({ item, on, onPick }: { item: Item; on: boolean; onPick: () => void }) {
  if (item.lesson) {
    const { line, saved } = item.lesson;
    const position = positionAt(line.moves_uci.split(" "), saved.ply);
    return <button className={`rcard ${on ? "on" : ""}`} onClick={onPick}>
      <ChessBoard fen={position.fen()} mini flipped={line.family_side === "black"} />
      <span className="rc-body"><small>{line.opening_family}</small><b><LineTitle line={line} /></b>
        <span className="bar"><i style={{ width: `${Math.round(saved.ply / saved.total * 100)}%` }} /></span>
        <span className="rc-foot"><span className="chip warn">{saved.ply}/{saved.total} learned</span><span className="chip plain">{sideName(line.family_side)}</span></span></span></button>;
  }
  const line = item.rep!;
  const position = positionAt(line.moves_uci.split(" "), line.moves_uci.split(" ").length);
  return <button className={`rcard ${on ? "on" : ""}`} onClick={onPick}>
    <ChessBoard fen={position.fen()} mini flipped={line.family_side === "black"} />
    <span className="rc-body"><small>{line.opening_family}</small><b><LineTitle line={line} /></b><Meter line={line} />
      <span className="rc-foot"><DueChip line={line} /><span className="chip plain">{sideName(line.family_side)}</span></span></span></button>;
}

function Detail({ item }: { item: Item }) {
  const { now, repertoire, startLearning, startReview } = useApp();
  if (item.lesson) {
    const { line, saved } = item.lesson;
    const moves = line.moves_uci.split(" ");
    const position = positionAt(moves, saved.ply);
    return <aside className="card detail" aria-label="Selected lesson">
      <p className="eyebrow">{line.opening_family} · {line.eco}</p><h2><LineTitle line={line} /></h2>
      <div className="big-status"><b>Lesson in progress</b><small>{saved.ply} of {saved.total} half-moves learned · playing {sideName(line.family_side)} · last opened {fmtDate(saved.at)}</small>
        <span className="bar" style={{ marginTop: 10 }}><i style={{ width: `${Math.round(saved.ply / saved.total * 100)}%` }} /></span></div>
      <div className="detail-actions"><button className="btn primary" onClick={() => void startLearning(line.line_id)}><Play size={16} /> Continue lesson</button>
        <button className="btn ghost" onClick={() => void startLearning(line.line_id, { restart: true })}><RotateCcw size={16} /> Start over</button></div>
      <div className="detail-board"><div className="board-frame"><ChessBoard fen={position.fen()} flipped={line.family_side === "black"} /></div></div>
      <MoveChips moves={moves} upTo={saved.ply} /></aside>;
  }
  const line = item.rep!;
  const moves = line.moves_uci.split(" ");
  const position = positionAt(moves, moves.length);
  const info = dueInfo(line, now, repertoire?.target_recall ?? 0.9);
  const last = line.reviews.at(-1);
  const due = isDue(line, now);
  // Days waited before each review: from learning (first review) or from the review before it.
  const gaps = line.reviews.map((review, index) => (Date.parse(review.at) - Date.parse(index ? line.reviews[index - 1].at : line.learned_at)) / DAY);
  const longest = Math.max(1, ...gaps);
  return <aside className="card detail" aria-label="Selected line">
    <p className="eyebrow">{line.opening_family} · {line.eco}</p><h2><LineTitle line={line} /></h2>
    <div className="big-status"><b>{info.long}</b><Meter line={line} /><small>{recallText(line)} · playing {sideName(line.family_side)}</small></div>
    <div className="detail-actions"><button className="btn primary" onClick={() => void startReview(line.line_id)}><RotateCcw size={16} /> {due ? "Review now" : "Practise early"}</button>
      <button className="btn ghost" onClick={() => void startLearning(line.line_id, { restart: true })}><BookOpen size={16} /> Learn again</button></div>
    <div className="detail-board"><div className="board-frame"><ChessBoard fen={position.fen()} flipped={line.family_side === "black"} /></div></div>
    <MoveChips moves={moves} />
    <div className="facts">
      <div className="fact"><span>Learned</span><b>{fmtDate(line.learned_at, { day: "numeric", month: "short" })}</b></div>
      <div className="fact"><span>Last review</span><b>{last ? <>{fmtDate(last.at, { day: "numeric", month: "short" })} <span className={`gt${gradeClass[last.grade].slice(1)}`}>{last.grade}</span></> : "Not yet"}</b></div>
      <div className="fact"><span>Next review</span><b>{due ? "Now" : fmtDate(line.next_review_at, { day: "numeric", month: "short" })}</b></div>
      <div className="fact"><span>Memory strength</span><b>{line.stability_days == null ? "Not measured" : `${line.stability_days.toFixed(1)} days`}</b></div>
    </div>
    <h3>How its memory grew</h3>
    {line.reviews.length ? <ul className="hist">{line.reviews.map((review, index) => <li key={review.at}>
      <span>{fmtDate(review.at, { day: "numeric", month: "short" })}</span><span className={`grade ${gradeClass[review.grade]}`}>{review.grade}</span>
      <span className="gap"><i style={{ width: `${Math.max(4, gaps[index] / longest * 55)}%` }} />after {gaps[index] < 1 ? "under a day" : plural(Math.round(gaps[index]), "day")}</span></li>)}</ul>
      : <p className="muted small" style={{ margin: "6px 0 0" }}>No reviews yet. The first recall test starts the memory clock.</p>}
    <p className="muted small" style={{ marginTop: 12 }}>{lineLabel(line)} · {moves.length} half-moves</p>
  </aside>;
}
