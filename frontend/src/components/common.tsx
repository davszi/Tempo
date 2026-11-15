import { positionAt } from "../lib/learning";
import { lineLabel } from "../lib/catalog";
import { dueInfo, isDue, recallLevel } from "../lib/memory";
import { useApp } from "../lib/app";
import { sideLabels, type OpeningLine, type RepertoireLine, type Side } from "../lib/practiceApi";

export const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;
export const fmtDate = (time: number | string, options: Intl.DateTimeFormatOptions = { weekday: "short", day: "numeric", month: "short" }) =>
  new Date(time).toLocaleDateString(undefined, options);
export const sideName = (side: Side) => sideLabels[side];

export function Toast({ text }: { text: string }) {
  return <div id="toast-root" aria-live="polite">{text && <div className="toast">{text}</div>}</div>;
}

export function SideDot({ side }: { side: Side }) {
  return <span className={`side-dot ${side}`} title={`Played as ${sideName(side)}`} />;
}

/** A line's variation name, plus the moves that tell it apart from same-named lines. */
export function LineTitle({ line }: { line: { line_id: number; name: string; opening_family: string } }) {
  const { variants } = useApp();
  const extra = variants.get(line.line_id);
  return <>{lineLabel(line)}{extra && <span className="alt"> {extra}</span>}</>;
}

/** The moves of a line as numbered chips; `upTo` hides the moves not yet reached. */
export function MoveChips({ moves, upTo, nextIndex }: { moves: string[]; upTo?: number; nextIndex?: number }) {
  const san = positionAt(moves, moves.length).history();
  return <div className="moves">{san.map((move, index) => {
    const hidden = upTo != null && index >= upTo && index !== nextIndex;
    return <span key={index} className={`mv ${index === nextIndex ? "next" : hidden ? "ghost" : ""}`}>
      {index % 2 === 0 && <small>{index / 2 + 1}.</small>}{hidden ? "?" : move}</span>;
  })}</div>;
}

/** Recall ring: the chance of recalling a line right now, as a small gauge. */
export function Ring({ line, size = 46 }: { line: RepertoireLine; size?: number }) {
  const { repertoire } = useApp();
  const target = repertoire?.target_recall ?? 0.9;
  const circumference = 2 * Math.PI * 18;
  if (line.recall == null) {
    return <span className="ring new" style={{ width: size, height: size }} title="Not tested yet">
      <svg viewBox="0 0 44 44"><circle cx="22" cy="22" r="18" className="track" /></svg><b>new</b></span>;
  }
  const percent = Math.round(line.recall * 100);
  return <span className={`ring ${recallLevel(line.recall, target)}`} style={{ width: size, height: size }} title={`${percent}% chance you recall it now`}>
    <svg viewBox="0 0 44 44"><circle cx="22" cy="22" r="18" className="track" />
      <circle cx="22" cy="22" r="18" className="val" strokeDasharray={`${(line.recall * circumference).toFixed(1)} ${circumference.toFixed(1)}`} /></svg>
    <b>{percent}%</b></span>;
}

/** Memory bar: the same chance of recall as a horizontal meter. */
export function Meter({ line }: { line: RepertoireLine }) {
  const { repertoire } = useApp();
  if (line.recall == null) return <span className="meter new" title="Not tested yet"><i style={{ width: "100%" }} /></span>;
  const level = recallLevel(line.recall, repertoire?.target_recall ?? 0.9);
  return <span className={`meter ${level === "ok" ? "" : level}`} title={`${Math.round(line.recall * 100)}% chance you recall it now`}>
    <i style={{ width: `${Math.round(line.recall * 100)}%` }} /></span>;
}

export const recallText = (line: RepertoireLine) => line.recall == null ? "Not tested yet" : `${Math.round(line.recall * 100)}% recall now`;

export function DueChip({ line }: { line: RepertoireLine }) {
  const { now, repertoire } = useApp();
  const info = dueInfo(line, now, repertoire?.target_recall ?? 0.9);
  return <span className={`chip ${info.tone}`} title={info.long}>{info.text}</span>;
}

/** A learned line as a compact card: recall ring, name, when it is due, and Review or Practise. */
export function MemCard({ line }: { line: RepertoireLine }) {
  const { now, startReview } = useApp();
  const due = isDue(line, now);
  return <div className={`mcard ${due ? "due" : ""}`}><Ring line={line} />
    <span className="mc-text"><b><LineTitle line={line} /></b><small>{line.opening_family} · {sideName(line.family_side)}</small><DueChip line={line} /></span>
    <button className={`btn sm ${due ? "primary" : "ghost"}`} onClick={() => void startReview(line.line_id)}>{due ? "Review" : "Practise"}</button></div>;
}

/** The same line as a full-width row, used in the review queue. */
export function MemRow({ line }: { line: RepertoireLine }) {
  const { now, startReview } = useApp();
  const due = isDue(line, now);
  return <div className="mem-row"><SideDot side={line.family_side} />
    <span><b><LineTitle line={line} /></b><small>{line.opening_family} · {sideName(line.family_side)}</small></span>
    <span className="mem-meter"><Meter line={line} /><small className="muted">{recallText(line)}</small></span>
    <DueChip line={line} />
    <button className={`btn sm ${due ? "primary" : "ghost"}`} onClick={() => void startReview(line.line_id)}>{due ? "Review" : "Practise"}</button></div>;
}

export const finalPosition = (line: OpeningLine | RepertoireLine, ply?: number) => {
  const moves = line.moves_uci.split(" ");
  return positionAt(moves, ply ?? moves.length);
};
