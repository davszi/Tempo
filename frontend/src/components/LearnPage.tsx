import { useEffect, useMemo, useState } from "react";
import { ArrowDownWideNarrow, LockKeyhole, Search, SlidersHorizontal } from "lucide-react";
import { learningSideKey, useApp, type LearningSide } from "../lib/app";
import { allOpeningTypes, linesByType, openingTypes, playerMoveCount } from "../lib/catalog";
import openingDifficulty from "../data/openingDifficulty.json";
import popularity from "../data/openingPopularity.json";
import { positionAt } from "../lib/learning";
import type { OpeningLine } from "../lib/practiceApi";
import { ChessBoard } from "./ChessBoard";
import { SideDot, plural, sideName } from "./common";

// Sample counts from 825e9d8:ml/ml_1000bots/openings/family_side_evidence.csv.
const popularityByFamily: Readonly<Partial<Record<string, number>>> = popularity;
const studyOrder = Object.values(openingDifficulty).flat();
const studyRankByFamily = new Map(studyOrder.map((name, index) => [name, index]));
const whiteDefenseMessage = "The Defenses filter is unavailable when playing White.";

/** Learning mode: every opening family, filtered by the side the player plays (opening_families.family_side). */
export function LearnPage() {
  const { families, progress, catalog, go, showToast, openingSort, setOpeningSort, availableOpeningTypes,
    selectedOpeningTypes, setSelectedOpeningTypes, learningSide: side, setLearningSide } = useApp();
  const [query, setQuery] = useState("");
  const [menu, setMenu] = useState<"sort" | "filter" | null>(null);
  const [draftOpeningTypes, setDraftOpeningTypes] = useState(selectedOpeningTypes);
  const [hoveredFamily, setHoveredFamily] = useState<string | null>(null);
  const chooseSide = (value: LearningSide) => {
    if (value !== side && menu === "filter") setMenu(null);
    setLearningSide(value);
    if (value === "white") {
      setSelectedOpeningTypes(selectedOpeningTypes.filter((type) => type !== "defense"));
      if (side !== "white") showToast(whiteDefenseMessage);
    } else if (value === "black" && side !== "black" && !selectedOpeningTypes.includes("defense")) {
      setSelectedOpeningTypes([...selectedOpeningTypes, "defense"]);
    }
    try { localStorage.setItem(learningSideKey, value); } catch { /* ignore */ }
  };

  const term = query.trim().toLowerCase();
  const allTypesSelected = selectedOpeningTypes.length === availableOpeningTypes.length;
  const cards = families.map((family) => {
    const nameHit = !term || family.name.toLowerCase().includes(term) || family.eco.toLowerCase().includes(term);
    const lines = linesByType(family, selectedOpeningTypes);
    const lineHits = term ? lines.filter((line) => line.name.toLowerCase().includes(term) || line.eco.toLowerCase() === term).length : 0;
    const learned = lines.filter((line) => line.learned).length;
    const inProgress = lines.filter((line) => progress[line.line_id]).length;
    const moveCounts = lines.map(playerMoveCount);
    return { family, lines, nameHit, lineHits, learned, inProgress,
      studyRank: studyRankByFamily.get(family.name) ?? studyOrder.length,
      shortestLineMoves: Math.min(...moveCounts),
      averageMoves: moveCounts.reduce((sum, count) => sum + count, 0) / moveCounts.length,
      popularity: popularityByFamily[family.name] ?? -1,
    };
  }).filter((card) => card.lines.length && (card.nameHit || card.lineHits));
  const visibleCards = cards.filter(({ family }) => side === "all" || family.side === side);
  visibleCards.sort((a, b) => (openingSort === "popular" ? b.popularity - a.popularity : a.studyRank - b.studyRank)
    || a.shortestLineMoves - b.shortestLineMoves || a.averageMoves - b.averageMoves
    || a.family.root.line_id - b.family.root.line_id);
  const lineCount = visibleCards.reduce((sum, card) => sum + card.lines.length, 0);
  const sections = openingSort === "easy"
    ? [
      ...Object.entries(openingDifficulty).map(([tier, names]) => ({
        title: tier[0].toUpperCase() + tier.slice(1),
        cards: visibleCards.filter(({ family }) => names.includes(family.name)),
      })),
      { title: "Unranked", cards: visibleCards.filter(({ studyRank }) => studyRank === studyOrder.length) },
    ].filter(({ cards }) => cards.length > 0)
    : [{ title: null, cards: visibleCards }];

  return <>
    <header className="page-head"><p className="eyebrow">LEARNING MODE</p><h1>Build your repertoire.</h1>
      <p className="lead">Every opening family in the TEMPO library. Open one to see all of its variations, pick a line, and follow the arrows on the board.</p></header>
    <div className="controls">
      <label className="search"><Search size={18} /><span className="sr">Search openings</span>
        <input type="search" placeholder="Search openings, variations or ECO codes" value={query} onChange={(event) => setQuery(event.target.value)} autoComplete="off" /></label>
      <div className="learning-browse-controls">
        <div className="seg" role="tablist" aria-label="Which side do you play">
          {([["all", "All openings"], ["white", "I play White"], ["black", "I play Black"]] as const).map(([value, label]) =>
            <button key={value} role="tab" aria-selected={side === value} className={side === value ? "on" : ""} onClick={() => chooseSide(value)}>
              {value !== "all" && <SideDot side={value} />}{label}
              <span className="n">{cards.filter(({ family }) => value === "all" || family.side === value).length}</span></button>)}
        </div>
        <div className="learning-filter">
          <button type="button" className={`btn sm ${menu === "sort" ? "primary" : "ghost"}`}
            aria-expanded={menu === "sort"} aria-controls="learning-sort"
            onClick={() => setMenu((open) => open === "sort" ? null : "sort")}>
            <ArrowDownWideNarrow size={16} aria-hidden="true" /> Sort
          </button>
          <div id="learning-sort" className="learning-menu" hidden={menu !== "sort"}>
            <fieldset aria-label="Sort openings">
              {([["easy", "Easy to hard"], ["popular", "Most popular"]] as const).map(([value, label]) =>
                <label key={value}><input type="radio" name="learning-sort" checked={openingSort === value}
                  onChange={() => setOpeningSort(value)} />{label}</label>)}
            </fieldset>
            <small className="muted">{openingSort === "popular" ? "Popularity uses a Lichess game sample."
              : "Study order considers opening plans, common replies, and how precisely you need to play."}</small>
          </div>
        </div>
        <div className="learning-filter">
          <button type="button" className={`btn sm ${menu === "filter" || !allTypesSelected ? "primary" : "ghost"}`}
            aria-expanded={menu === "filter"} aria-controls="learning-types"
            onClick={() => {
              if (menu !== "filter") setDraftOpeningTypes(selectedOpeningTypes);
              setMenu(menu === "filter" ? null : "filter");
            }}>
            <SlidersHorizontal size={16} aria-hidden="true" /> Filter
          </button>
          <div id="learning-types" className="learning-menu" hidden={menu !== "filter"}>
            <fieldset aria-labelledby="opening-type-heading">
              <div className="learning-type-heading">
                <span id="opening-type-heading">Opening type</span>
                <button type="button" className="btn sm ghost" onClick={() => setDraftOpeningTypes([])}>
                  Clear all
                </button>
              </div>
              {openingTypes.map(([value, label]) => {
                const unavailable = !availableOpeningTypes.includes(value);
                return <label key={value} className={unavailable ? "learning-type-locked" : undefined}>
                  <input type="checkbox" checked={draftOpeningTypes.includes(value)} aria-disabled={unavailable || undefined}
                    onClick={(event) => {
                      if (unavailable) {
                        event.preventDefault();
                        showToast(whiteDefenseMessage);
                      }
                    }}
                    onChange={(event) => {
                      if (!unavailable) {
                        const checked = event.target.checked;
                        setDraftOpeningTypes((types) => checked
                          ? [...types, value]
                          : types.filter((type) => type !== value));
                      }
                    }} />
                  {label}{unavailable && <LockKeyhole size={14} aria-hidden="true" />}
                </label>;
              })}
            </fieldset>
            <button type="button" className="btn sm primary" onClick={() => {
              setSelectedOpeningTypes(draftOpeningTypes);
              setMenu(null);
            }}>Apply filters</button>
          </div>
        </div>
      </div>
    </div>
    {catalog.length > 0 && <p className="result-count">{visibleCards.length} {side === "all" ? "" : `${sideName(side)} `}opening {visibleCards.length === 1 ? "family" : "families"} · {lineCount.toLocaleString()} lines to learn</p>}
    {catalog.length === 0 ? <div className="empty">Loading openings…</div>
      : visibleCards.length ? <div className="learning-sections">{sections.map(({ title, cards }) => (
        <section key={title ?? "popular"} aria-label={title ?? undefined}>
          {title && <h2 className="learning-tier-title">{title}</h2>}
          <div className="fam-grid">{cards.map(({ family, lines, lineHits, learned, inProgress }) => {
            return <button key={family.name} className="fam" onClick={() => go(`#/family/${encodeURIComponent(family.name)}`)}
              onPointerEnter={(event) => { if (event.pointerType !== "touch") setHoveredFamily(family.name); }}
              onPointerLeave={() => setHoveredFamily(null)}>
              <OpeningPreview line={selectedOpeningTypes.length === allOpeningTypes.length ? family.root : lines[0]} flipped={family.side === "black"} playing={hoveredFamily === family.name} />
              <div className="fam-body"><h3>{family.name}</h3>
                <div className="fam-meta"><span>{plural(lines.length, "line")}</span><span>{family.eco}</span>
                  <span className="side-tag"><SideDot side={family.side} />{sideName(family.side)}</span></div>
                {lineHits > 0 && <span className="chip">{plural(lineHits, "matching line")}</span>}
                <div className="fam-progress"><span className="bar"><i style={{ width: `${Math.round(learned / lines.length * 100)}%` }} /></span>
                  <span>{learned}/{lines.length}</span></div>
                {inProgress > 0 && <span className="chip warn">{inProgress} in progress</span>}
              </div></button>;
          })}</div>
        </section>
      ))}</div>
      : <div className="empty"><h3>No openings match</h3>Try another search or change your filters.</div>}
  </>;
}

/** A family card's board: six half-moves at rest, the whole line played out while hovered. */
export function OpeningPreview({ line, flipped, playing }: { line: OpeningLine; flipped: boolean; playing: boolean }) {
  const moves = useMemo(() => line.moves_uci.split(" "), [line.moves_uci]);
  const [ply, setPly] = useState(0);
  useEffect(() => {
    setPly(0);
    if (!playing) return;
    let nextPly = 0;
    const timer = window.setInterval(() => {
      nextPly += 1;
      setPly(nextPly);
      if (nextPly >= moves.length) window.clearInterval(timer);
    }, 400);
    return () => window.clearInterval(timer);
  }, [moves, playing]);

  const shown = playing ? ply : Math.min(6, moves.length);
  const preview = useMemo(() => positionAt(moves, shown), [moves, shown]);
  return <ChessBoard fen={preview.fen()} mini flipped={flipped} lastMove={preview.history({ verbose: true }).at(-1)} />;
}
