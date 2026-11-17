import { useEffect, useState } from "react";
import { ArrowLeft, BookOpen, ChevronRight, Play, RotateCcw, Search } from "lucide-react";
import { useApp } from "../lib/app";
import { type Family, lineLabel, playerMoveCount, progressMoves } from "../lib/catalog";
import { DAY, dueAt, dueInfo, isDue } from "../lib/memory";
import { positionAt } from "../lib/learning";
import type { OpeningLine, RepertoireLine } from "../lib/practiceApi";
import type { LessonProgress } from "../lib/progress";
import { ChessBoard } from "./ChessBoard";
import { DueChip, LineTitle, Meter, MoveChips, SideDot, fmtDate, plural, recallText, sideName } from "./common";
import { OpeningPreview } from "./LearnPage";

const TABS = [
  ["all", "All families", "", "Every opening family you've started, most urgent first."],
  ["due", "Review now", "var(--again)", "Families with at least one line whose recall has dropped to your target."],
  ["fresh", "Fresh", "var(--good)", "Families whose learned lines are all remembered well for now."],
  ["learning", "Still learning", "var(--hard)", "Families with a lesson you started but haven't finished."],
] as const;
type Tab = typeof TABS[number][0];
type Lesson = { line: OpeningLine; saved: LessonProgress };
/** One row of a family's line list: a learned line, an unfinished lesson, or a line not started yet. */
type Item = { key: string; rep?: RepertoireLine; lesson?: Lesson; fresh?: OpeningLine };
const gradeClass = { Again: "g1", Hard: "g2", Good: "g3", Easy: "g4" } as const;

/** The repertoire: opening families you've started, or one family's lines when `family` is given. */
export function RepertoirePage({ family }: { family?: string }) {
  return family ? <RepertoireFamily name={family} /> : <RepertoireFamilies />;
}

/** What the player has in one family: learned lines (most urgent first) and unfinished lessons. */
function familyState(family: Family, lines: RepertoireLine[], lessons: Lesson[], now: number) {
  const learned = lines.filter((line) => line.opening_family === family.name).sort((a, b) => dueAt(a) - dueAt(b));
  const started = lessons.filter((lesson) => lesson.line.opening_family === family.name);
  const due = learned.filter((line) => isDue(line, now));
  const tested = learned.filter((line) => line.recall != null);
  const weakest = tested.length ? tested.reduce((low, line) => (line.recall! < low.recall! ? line : low)) : undefined;
  return { family, learned, started, due, weakest };
}

function RepertoireFamilies() {
  const { repertoire, progress, lineById, families, now, go } = useApp();
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");
  const [side, setSide] = useState<"all" | "white" | "black">("all");
  const [hovered, setHovered] = useState<string | null>(null);
  const head = <header className="page-head"><p className="eyebrow">REPERTOIRE</p><h1>Your openings, at a glance.</h1>
    <p className="lead">Every opening family you've started. Open one to see the lines you've learned, how well you remember each, and the rest of the family.</p></header>;
  const lines = repertoire?.lines ?? [];
  const lessons: Lesson[] = Object.entries(progress).map(([id, saved]) => ({ line: lineById.get(Number(id)), saved }))
    .filter((item): item is Lesson => !!item.line);
  if (!repertoire || !families.length) return <>{head}<div className="empty">Loading your repertoire…</div></>;
  if (!lines.length && !lessons.length) {
    return <>{head}<div className="card"><div className="steps">
      <div><span className="step-n">1</span><b>Learn a line</b><small>Follow the arrows in Learning mode.</small></div>
      <div><span className="step-n">2</span><b>It lands here</b><small>With a memory bar that slowly drains.</small></div>
      <div><span className="step-n">3</span><b>Review in time</b><small>TEMPO calls it back before you forget.</small></div></div>
      <div style={{ textAlign: "center", marginTop: 18 }}><button className="btn primary" onClick={() => go("#/learn")}><BookOpen size={16} /> Learn your first line</button></div></div></>;
  }

  const started = families.map((family) => familyState(family, lines, lessons, now))
    .filter((state) => state.learned.length || state.started.length)
    // Most urgent first: families with due lines, then the soonest next review, then those only in progress.
    .sort((a, b) => b.due.length - a.due.length
      || (a.learned.length ? dueAt(a.learned[0]) : Infinity) - (b.learned.length ? dueAt(b.learned[0]) : Infinity)
      || a.family.name.localeCompare(b.family.name));
  const inTab = (state: ReturnType<typeof familyState>, id: Tab) => id === "all" || (id === "due" ? state.due.length > 0
    : id === "fresh" ? state.learned.length > 0 && !state.due.length : state.started.length > 0);
  const term = query.trim().toLowerCase();
  const matches = (state: ReturnType<typeof familyState>) => (side === "all" || state.family.side === side) && (!term
    || `${state.family.name} ${state.family.eco}`.toLowerCase().includes(term)
    || [...state.learned, ...state.started.map((lesson) => lesson.line)].some((line) => `${line.name} ${line.eco}`.toLowerCase().includes(term)));
  const counts = Object.fromEntries(TABS.map(([id]) => [id, started.filter((state) => inTab(state, id)).length])) as Record<Tab, number>;
  const shown = started.filter((state) => inTab(state, tab) && matches(state));
  const current = TABS.find((item) => item[0] === tab)!;

  return <>{head}
    <div className="seg" role="tablist" aria-label="Filter by status">{TABS.map(([id, label, dot]) =>
      <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
        {dot && <span className="dot" style={{ background: dot }} />}{label}<span className="n">{counts[id]}</span></button>)}</div>
    <p className="tab-help">{current[3]}</p>
    <div className="controls">
      <label className="search"><Search size={18} /><span className="sr">Search your openings</span>
        <input type="search" placeholder="Search by opening, variation or ECO" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /></label>
      <div className="chips">{([["all", "All sides"], ["white", "White"], ["black", "Black"]] as const).map(([value, label]) =>
        <button key={value} className={`fchip ${side === value ? "on" : ""}`} onClick={() => setSide(value)}>{label}</button>)}</div>
    </div>
    {shown.length ? <div className="fam-grid">{shown.map(({ family, learned, started: inProgress, due, weakest }) =>
      <button key={family.name} className="fam" onClick={() => go(`#/repertoire/${encodeURIComponent(family.name)}`)}
        onPointerEnter={(event) => { if (event.pointerType !== "touch") setHovered(family.name); }} onPointerLeave={() => setHovered(null)}>
        <OpeningPreview line={family.root} flipped={family.side === "black"} playing={hovered === family.name} />
        <div className="fam-body"><h3>{family.name}</h3>
          <div className="fam-meta"><span>{learned.length} of {plural(family.lines.length, "line")} learned</span><span>{family.eco}</span>
            <span className="side-tag"><SideDot side={family.side} />{sideName(family.side)}</span></div>
          <div className="fam-progress"><span className="bar"><i style={{ width: `${Math.round(learned.length / family.lines.length * 100)}%` }} /></span>
            <span>{learned.length}/{family.lines.length}</span></div>
          {weakest && <div className="fam-recall"><Meter line={weakest} /><small>Weakest {Math.round(weakest.recall! * 100)}% recall now</small></div>}
          <div className="rc-foot">
            {due.length > 0 && <span className="chip bad">{due.length} due</span>}
            {inProgress.length > 0 && <span className="chip warn">{inProgress.length} in progress</span>}
            {learned.length > 0 && !due.length && <DueChip line={learned[0]} />}
          </div>
        </div></button>)}</div>
      : <div className="empty">{tab === "due" && !term ? "Nothing needs a review right now. Nice." : tab === "learning" && !term ? "No unfinished lessons." : "No opening matches."}</div>}
  </>;
}

/** One family in the repertoire: learned lines first with their memory, then lessons in progress, then the rest. */
function RepertoireFamily({ name }: { name: string }) {
  const { repertoire, progress, lineById, families, now, openingSort, go } = useApp();
  const [query, setQuery] = useState("");
  const [picked, setPicked] = useState<string | null>(null);
  useEffect(() => { setQuery(""); setPicked(null); }, [name]);
  const family = families.find((item) => item.name === name);
  if (!family || !repertoire) {
    return families.length && repertoire ? <div className="empty"><h3>Opening not found</h3>
      <button className="btn ghost" onClick={() => go("#/repertoire")}>Back to your repertoire</button></div>
      : <div className="empty">Loading your repertoire…</div>;
  }
  const lessons: Lesson[] = Object.entries(progress).map(([id, saved]) => ({ line: lineById.get(Number(id)), saved }))
    .filter((item): item is Lesson => !!item.line);
  const { learned, started, due } = familyState(family, repertoire.lines, lessons, now);
  const taken = new Set([...learned.map((line) => line.line_id), ...started.map((lesson) => lesson.line.line_id)]);
  const rest = family.lines.filter((line) => !taken.has(line.line_id));
  if (openingSort === "easy") rest.sort((a, b) => playerMoveCount(a) - playerMoveCount(b));
  const groups: [string, Item[]][] = [
    ["Learned", learned.map((rep) => ({ key: `r${rep.line_id}`, rep }))],
    ["In progress", started.sort((a, b) => b.saved.at - a.saved.at).map((lesson) => ({ key: `p${lesson.line.line_id}`, lesson }))],
    ["Not learned yet", rest.map((line) => ({ key: `n${line.line_id}`, fresh: line }))],
  ];
  const term = query.trim().toLowerCase();
  const itemLine = (item: Item) => (item.rep ?? item.lesson?.line ?? item.fresh)!;
  const hit = (item: Item) => !term || `${lineLabel(itemLine(item))} ${itemLine(item).eco}`.toLowerCase().includes(term);
  const all = groups.flatMap(([, items]) => items);
  const selected = all.find((item) => item.key === picked) ?? all[0];

  function pick(key: string) {
    setPicked(key);
    if (window.innerWidth <= 1100) requestAnimationFrame(() => document.querySelector(".detail")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  return <>
    <button className="back" onClick={() => go("#/repertoire")}><ArrowLeft size={16} /> Your repertoire</button>
    <header className="page-head fam-head"><div><p className="eyebrow">REPERTOIRE · {family.eco}</p><h1>{family.name}</h1>
      <p className="lead">{learned.length} of {plural(family.lines.length, "line")} learned{due.length ? ` · ${due.length} due` : ""}{started.length ? ` · ${started.length} in progress` : ""}</p></div>
      <span className="side-badge"><SideDot side={family.side} />You play {sideName(family.side)} in this opening</span></header>
    <div className="fam-layout">
      {selected && <Detail item={selected} family={family} />}
      <section className="card fam-vars" aria-label="Lines in this opening">
        <div className="row" style={{ marginBottom: 12 }}><h2>Lines</h2><span className="chip plain">{family.lines.length}</span></div>
        <label className="search" style={{ maxWidth: "none", marginBottom: 12 }}><Search size={18} /><span className="sr">Search this opening</span>
          <input type="search" placeholder="Search variations or ECO" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /></label>
        <div className="var-list" role="list">
          {groups.map(([label, items]) => {
            const visible = items.filter(hit);
            return visible.length ? <div key={label} className="var-group" role="presentation">
              <p className="var-group-head">{label} · {visible.length}</p>
              {visible.map((item) => <LineRow key={item.key} item={item} on={item.key === selected?.key} onPick={() => pick(item.key)} />)}
            </div> : null;
          })}
          {!all.some(hit) && <div className="empty">No line matches.</div>}
        </div>
      </section>
    </div>
  </>;
}

function LineRow({ item, on, onPick }: { item: Item; on: boolean; onPick: () => void }) {
  const line = (item.rep ?? item.lesson?.line ?? item.fresh)!;
  return <button role="listitem" className={`var ${on ? "on" : ""}`} onClick={onPick}>
    <span className="grow"><b><LineTitle line={line} /></b><small>{line.eco} · {plural(playerMoveCount(line), "move")}</small></span>
    {item.rep ? <span className="var-memory"><Meter line={item.rep} /><small>{recallText(item.rep)}</small><DueChip line={item.rep} /></span>
      : item.lesson ? <span className="chip warn">{progressMoves(item.lesson.saved).done}/{progressMoves(item.lesson.saved).total}</span> : null}
    <ChevronRight size={16} /></button>;
}

function Detail({ item, family }: { item: Item; family: Family }) {
  const { now, repertoire, startLearning, startReview } = useApp();
  if (item.fresh) {
    const line = item.fresh;
    const moves = line.moves_uci.split(" ");
    const position = positionAt(moves, moves.length);
    return <aside className="card detail" aria-label="Selected line">
      <p className="eyebrow">{line.eco} · {plural(playerMoveCount(line), "move")}</p><h2><LineTitle line={line} /></h2>
      <div className="big-status"><b>Not learned yet</b><small>Learn it with arrows; it joins your repertoire when you finish.</small></div>
      <div className="detail-actions"><button className="btn primary" onClick={() => void startLearning(line.line_id, { restart: true })}>
        <Play size={16} /> Start learning as {sideName(family.side)}</button></div>
      <div className="detail-board"><div className="board-frame"><ChessBoard fen={position.fen()} flipped={family.side === "black"} /></div></div>
      <MoveChips moves={moves} /></aside>;
  }
  if (item.lesson) {
    const { line, saved } = item.lesson;
    const moves = line.moves_uci.split(" ");
    const position = positionAt(moves, saved.ply);
    const done = progressMoves(saved);
    return <aside className="card detail" aria-label="Selected lesson">
      <p className="eyebrow">{line.opening_family} · {line.eco}</p><h2><LineTitle line={line} /></h2>
      <div className="big-status"><b>Lesson in progress</b><small>{done.done} of {plural(done.total, "move")} learned · playing {sideName(line.family_side)} · last opened {fmtDate(saved.at)}</small>
        <span className="bar" style={{ marginTop: 10 }}><i style={{ width: `${Math.round(done.done / done.total * 100)}%` }} /></span></div>
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
    <p className="muted small" style={{ marginTop: 12 }}>{lineLabel(line)} · {plural(playerMoveCount(line), "move")}</p>
  </aside>;
}
