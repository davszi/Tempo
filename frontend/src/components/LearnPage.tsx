import { useState } from "react";
import { Search } from "lucide-react";
import { useApp } from "../lib/app";
import { ChessBoard } from "./ChessBoard";
import { SideDot, finalPosition, plural, sideName } from "./common";

type SideFilter = "all" | "white" | "black";
const FILTER_KEY = "tempo-learning-side";

/** Learning mode: every opening family, filtered by the side the player plays (opening_families.family_side). */
export function LearnPage() {
  const { families, progress, catalog, go } = useApp();
  const [query, setQuery] = useState("");
  const [side, setSide] = useState<SideFilter>(() => {
    const saved = localStorage.getItem(FILTER_KEY);
    return saved === "white" || saved === "black" ? saved : "all";
  });
  const chooseSide = (value: SideFilter) => { setSide(value); try { localStorage.setItem(FILTER_KEY, value); } catch { /* ignore */ } };

  const term = query.trim().toLowerCase();
  const cards = families.map((family) => {
    const nameHit = !term || family.name.toLowerCase().includes(term) || family.eco.toLowerCase().includes(term);
    const lineHits = term ? family.lines.filter((line) => line.name.toLowerCase().includes(term) || line.eco.toLowerCase() === term).length : 0;
    const learned = family.lines.filter((line) => line.learned).length;
    const inProgress = family.lines.filter((line) => progress[line.line_id]).length;
    return { family, nameHit, lineHits, learned, inProgress };
  }).filter((card) => (card.nameHit || card.lineHits) && (side === "all" || card.family.side === side));
  const lineCount = cards.reduce((sum, card) => sum + card.family.lines.length, 0);

  return <>
    <header className="page-head"><p className="eyebrow">LEARNING MODE</p><h1>Build your repertoire.</h1>
      <p className="lead">Every opening family in the TEMPO library. Open one to see all of its variations, pick a line, and follow the arrows on the board.</p></header>
    <div className="controls">
      <label className="search"><Search size={18} /><span className="sr">Search openings</span>
        <input type="search" placeholder="Search openings, variations or ECO codes" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /></label>
      <div className="seg" role="tablist" aria-label="Which side do you play">
        {([["all", "All openings"], ["white", "I play White"], ["black", "I play Black"]] as const).map(([value, label]) =>
          <button key={value} role="tab" aria-selected={side === value} className={side === value ? "on" : ""} onClick={() => chooseSide(value)}>
            {value !== "all" && <SideDot side={value} />}{label}
            <span className="n">{value === "all" ? families.length : families.filter((family) => family.side === value).length}</span></button>)}
      </div>
    </div>
    {catalog.length > 0 && <p className="result-count">{cards.length} {side === "all" ? "" : `${sideName(side)} `}opening {cards.length === 1 ? "family" : "families"} · {lineCount.toLocaleString()} lines to learn</p>}
    {catalog.length === 0 ? <div className="empty">Loading openings…</div>
      : cards.length ? <div className="fam-grid">{cards.map(({ family, lineHits, learned, inProgress }) => {
        const preview = finalPosition(family.root, Math.min(6, family.root.moves_uci.split(" ").length));
        return <button key={family.name} className="fam" onClick={() => go(`#/family/${encodeURIComponent(family.name)}`)}>
          <ChessBoard fen={preview.fen()} mini flipped={family.side === "black"} lastMove={preview.history({ verbose: true }).at(-1)} />
          <div className="fam-body"><h3>{family.name}</h3>
            <div className="fam-meta"><span>{plural(family.lines.length, "line")}</span><span>{family.eco}</span>
              <span className="side-tag"><SideDot side={family.side} />{sideName(family.side)}</span></div>
            {lineHits > 0 && <span className="chip">{plural(lineHits, "matching line")}</span>}
            <div className="fam-progress"><span className="bar"><i style={{ width: `${Math.round(learned / family.lines.length * 100)}%` }} /></span>
              <span>{learned}/{family.lines.length}</span></div>
            {inProgress > 0 && <span className="chip warn">{inProgress} in progress</span>}
          </div></button>;
      })}</div>
      : <div className="empty"><h3>No openings match</h3>Try another name, a variation, or an ECO code such as C50.</div>}
  </>;
}
