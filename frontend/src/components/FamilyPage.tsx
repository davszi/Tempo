import { useEffect, useState } from "react";
import { ArrowLeft, BookOpen, Check, ChevronRight, Play, RotateCcw, Search } from "lucide-react";
import { useApp } from "../lib/app";
import { lineLabel } from "../lib/catalog";
import { positionAt } from "../lib/learning";
import { ChessBoard } from "./ChessBoard";
import { LineTitle, MoveChips, SideDot, plural, sideName } from "./common";

/** One opening family: the chosen line on a board on the left, every learnable variation on the right. */
export function FamilyPage({ name }: { name: string }) {
  const { families, progress, repertoire, go, startLearning, startReview } = useApp();
  const family = families.find((item) => item.name === name);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  useEffect(() => { setQuery(""); setSelectedId(null); }, [name]);

  if (!family) {
    return families.length ? <div className="empty"><h3>Opening not found</h3><button className="btn ghost" onClick={() => go("#/learn")}>Back to openings</button></div>
      : <div className="empty">Loading openings…</div>;
  }
  const term = query.trim().toLowerCase();
  const list = family.lines.filter((line) => !term || lineLabel(line).toLowerCase().includes(term) || line.eco.toLowerCase().includes(term)
    || positionAt(line.moves_uci.split(" "), line.moves_uci.split(" ").length).history().join(" ").toLowerCase().includes(term));
  const selected = family.lines.find((line) => line.line_id === selectedId) ?? family.lines.find((line) => !line.learned) ?? family.lines[0];
  const moves = selected.moves_uci.split(" ");
  const position = positionAt(moves, moves.length);
  const saved = progress[selected.line_id];
  const inRepertoire = repertoire?.lines.some((line) => line.line_id === selected.line_id);
  const learnedCount = family.lines.filter((line) => line.learned).length;
  const inProgress = family.lines.filter((line) => progress[line.line_id]).length;

  return <>
    <button className="back" onClick={() => go("#/learn")}><ArrowLeft size={16} /> All openings</button>
    <header className="page-head fam-head"><div><p className="eyebrow">OPENING FAMILY · {family.eco}</p><h1>{family.name}</h1>
      <p className="lead">{plural(family.lines.length, "line")} to learn · {learnedCount} learned{inProgress ? ` · ${inProgress} in progress` : ""}</p></div>
      <span className="side-badge"><SideDot side={family.side} />You play {sideName(family.side)} in this opening</span></header>
    <div className="fam-layout">
      <section className="card fam-stage" aria-label="Selected line">
        <div className="fam-info">
          <div><p className="eyebrow">{selected.eco} · {moves.length} half-moves</p><h2><LineTitle line={selected} /></h2></div>
          <div className="fam-actions">
            {saved ? <>
              <button className="btn primary" onClick={() => void startLearning(selected.line_id)}><Play size={16} /> Continue ({saved.ply}/{saved.total})</button>
              <button className="btn ghost" onClick={() => void startLearning(selected.line_id, { restart: true })}><RotateCcw size={16} /> Start over</button>
            </> : inRepertoire ? <>
              <button className="btn primary" onClick={() => void startReview(selected.line_id)}><RotateCcw size={16} /> Review without hints</button>
              <button className="btn ghost" onClick={() => void startLearning(selected.line_id, { restart: true })}><BookOpen size={16} /> Learn again</button>
            </> : <button className="btn primary" onClick={() => void startLearning(selected.line_id, { restart: true })}><Play size={16} /> Start learning as {sideName(family.side)}</button>}
          </div>
        </div>
        <div className="fam-board"><div className="board-frame">
          <ChessBoard fen={position.fen()} flipped={family.side === "black"} lastMove={position.history({ verbose: true }).at(-1)} /></div></div>
        <MoveChips moves={moves} />
      </section>
      <section className="card fam-vars" aria-label="All variations">
        <div className="row" style={{ marginBottom: 12 }}><h2>All variations</h2><span className="chip plain">{list.length}</span></div>
        <label className="search" style={{ maxWidth: "none", marginBottom: 12 }}><Search size={18} /><span className="sr">Search this opening</span>
          <input type="search" placeholder="Search variations or moves" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /></label>
        <div className="var-list" role="list">{list.length ? list.map((line) => {
          const lineProgress = progress[line.line_id];
          return <button key={line.line_id} role="listitem" className={`var ${line.line_id === selected.line_id ? "on" : ""}`} onClick={() => setSelectedId(line.line_id)}>
            <span className="grow"><b><LineTitle line={line} /></b><small>{line.eco} · {line.moves_uci.split(" ").length} half-moves</small></span>
            {line.learned ? <span className="chip"><Check size={12} /> Learned</span> : lineProgress ? <span className="chip warn">{lineProgress.ply}/{lineProgress.total}</span> : null}
            <ChevronRight size={16} /></button>;
        }) : <div className="empty">No variation matches.</div>}</div>
      </section>
    </div>
  </>;
}
