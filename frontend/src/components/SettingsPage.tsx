import { Crown, Palette, Sparkles } from "lucide-react";
import { PIECE_CREDITS, PIECE_SETS, THEMES, pieceImage, type Appearance, type PieceSetId } from "../lib/appearance";
import { positionAt } from "../lib/learning";
import { ChessBoard } from "./ChessBoard";

const PREVIEW = positionAt("e2e4 e7e5 g1f3 b8c6 f1c4 f8c5 c2c3 g8f6".split(" "), 8);

export function SettingsPage({ appearance, onChange }: { appearance: Appearance; onChange: (next: Appearance) => void }) {
  const theme = THEMES.find((item) => item.id === appearance.theme) ?? THEMES[0];
  const set = PIECE_SETS.find((item) => item.id === appearance.pieces) ?? PIECE_SETS[0];
  const sample = (pieces: PieceSetId) => ([["wK", "l"], ["bQ", "d"], ["wN", "d"], ["bN", "l"]] as const).map(([code, square]) =>
    <span key={code} className={`s ${square}`}><span className="pc"><img src={pieceImage(pieces, code, appearance.theme)} alt="" /></span></span>);
  function surprise() {
    const others = <T extends { id: string }>(list: readonly T[], current: string) => list.filter((item) => item.id !== current);
    const nextTheme = others(THEMES, appearance.theme), nextPieces = others(PIECE_SETS, appearance.pieces);
    onChange({ theme: nextTheme[Math.floor(Math.random() * nextTheme.length)].id, pieces: nextPieces[Math.floor(Math.random() * nextPieces.length)].id });
  }
  return <>
    <header className="page-head"><p className="eyebrow">SETTINGS</p><h1>Make TEMPO yours.</h1>
      <p className="lead">Pick a theme and a piece set. The pieces take on the colours of the theme.</p></header>
    <section className="card"><div className="appearance">
      <div className="ap-preview"><div className="board-frame"><ChessBoard fen={PREVIEW.fen()} arrow={{ from: "e1", to: "g1" }} /></div>
        <p className="muted small"><b style={{ color: "var(--ink)" }}>{theme.name}</b> theme with <b style={{ color: "var(--ink)" }}>{set.name}</b> pieces · Italian Game</p>
        <button className="btn ghost" onClick={surprise}><Sparkles size={16} /> Surprise me</button></div>
      <div>
        <h2 className="ap-title"><Palette size={18} /> Theme</h2><p className="ap-sub">Colours for the whole app, the board and the pieces.</p>
        <div className="themes">{THEMES.map((item) => <button key={item.id} className={`theme ${appearance.theme === item.id ? "on" : ""}`}
          aria-pressed={appearance.theme === item.id} onClick={() => onChange({ ...appearance, theme: item.id })}>
          <span className="theme-board">{(["wK", "bQ", "wN", "bN"] as const).map((code, k) =>
            <i key={code} style={{ background: item.board[k % 2] }}><img src={pieceImage(appearance.pieces, code, item.id)} alt="" /></i>)}</span>
          <b>{item.name}</b><small>{item.note}</small></button>)}</div>
        <h2 className="ap-title" style={{ marginTop: 26 }}><Crown size={18} /> Pieces</h2><p className="ap-sub">Every set is recoloured to match the theme you pick.</p>
        <div className="themes">{PIECE_SETS.map((item) => <button key={item.id} className={`theme ${appearance.pieces === item.id ? "on" : ""}`}
          aria-pressed={appearance.pieces === item.id} onClick={() => onChange({ ...appearance, pieces: item.id })}>
          <span className="pset-board">{sample(item.id)}</span><b>{item.name}</b><small>{item.note}</small></button>)}</div>
        <p className="credits">{PIECE_CREDITS}</p>
      </div>
    </div></section>
  </>;
}
