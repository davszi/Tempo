"""Classify the Lichess chess-openings list.

    python openings/classify.py

Reads  openings/lichess_openings.tsv          (eco, name, pgn; Lichess, CC0)
Writes openings/lichess_openings_classified.csv

Columns
  eco, eco_letter, eco_group   ECO code, its volume letter and what the volume mainly
                               covers (Lichess also files transpositions under a code,
                               so some lines start differently, e.g. Catalan lines
                               reached via 1.d4 d5)
  family                       part of the name before ":" (", with ..." suffixes and
                               the one "Queen's Pawn, ..." spelling folded in)
  family_qualifier             ", with ..." part of the family name, if any
                               ("London System, with Bd3" -> family "London System",
                               qualifier "with Bd3")
  variation, subvariation      first part after ":" and the rest
  base_opening                 family with " Accepted"/" Declined" removed
                               (King's Gambit Accepted -> King's Gambit)
  family_side                  side whose repertoire choice the family is, set by
                               hand for every base opening (FAMILY_SIDE below):
                               "Sicilian Defense" -> black, "Ruy Lopez" -> white,
                               catch-all families follow their first named move
                               ("Queen's Pawn Game" -> white, 1.d4). Accepted /
                               Declined families take the side of their base
                               opening, the gambit player: in real games it is the
                               King's Gambit player who keeps reaching "King's
                               Gambit Accepted". "both" only for the Four Knights
                               Game (3.Nc3 from white and 3...Nf6 from black).
  side_in_games, side_ratio,   evidence from real Lichess games, if
  n_games                      family_side_evidence.csv exists (side_evidence.py):
                               which side's players keep returning to the family.
                               side_ratio >= 2 -> white, <= 0.5 -> black, in between
                               -> both (players of both sides meet it regularly,
                               e.g. Slav Defense), too few games -> empty
  plies                        half-moves in the line
  white_moves, black_moves     moves each side has to know
  last_mover                   side that plays the last move of the line (a fact
                               from the move list, not a judgement)
  name, pgn                    unchanged from Lichess. 688 names occur more than
                               once with different move orders (transpositions to
                               the same opening); no move sequence occurs twice.
"""
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))

ECO_GROUP = {
    "A": "mainly flank openings, and 1.d4 without 1...d5 not covered by E",
    "B": "mainly semi-open games: 1.e4 without 1...e5 or 1...e6",
    "C": "mainly open games 1.e4 e5, and the French Defense 1.e4 e6",
    "D": "mainly closed games 1.d4 d5, and the Grünfeld",
    "E": "mainly Indian systems 1.d4 Nf6 2.c4 e6 / g6 (incl. Catalan, King's Indian)",
}

WHITE = """
Amar Opening; Amazon Attack; Amsterdam Attack; Anderssen's Opening; Barnes Opening;
Basque Opening; Bird Opening;
Bishop's Opening; Blackmar-Diemer Gambit; Bongcloud Attack; Canard Opening; Catalan Opening; Center Game; Clemenz Opening;
Colle System; Creepy Crawly Formation; Danish Gambit; Dresden Opening;
English Opening; English Orangutan; Formation;
Global Opening; Grob Opening; Hungarian Opening; Irish Gambit; Italian Game;
King's Gambit; King's Indian Attack; King's Knight Opening; King's Pawn Game;
King's Pawn Opening; Kádas Opening; London System;
Mieses Opening; Nimzo-Larsen Attack; Paleface Attack; Polish Opening;
Ponziani Opening; Portuguese Opening; Queen's Gambit; Queen's Pawn Game;
Rapport-Jobava System; Richter-Veresov Attack; Rubinstein Opening; Ruy Lopez;
Réti Opening; Saragossa Opening; Scotch Game; Sodium Attack; Three Knights Opening;
Torre Attack; Trompowsky Attack; Valencia Opening; Van Geet Opening;
Van't Kruijs Opening; Vienna Gambit; Vienna Game; Ware Opening;
Yusupov-Rubinstein System; Zukertort Opening
"""
BLACK = """
Alekhine Defense; Australian Defense; Barnes Defense; Benko Gambit; Benoni Defense;
Blumenfeld Countergambit; Bogo-Indian Defense; Borg Defense; Caro-Kann Defense;
Carr Defense; Czech Defense; Duras Gambit; Dutch Defense; Döry Defense;
East Indian Defense; Elephant Gambit; English Defense; Englund Gambit;
French Defense; Fried Fox Defense; Goldsmith Defense; Grünfeld Defense;
Gunderam Defense; Hippopotamus Defense; Horwitz Defense; Indian Defense;
Kangaroo Defense; King's Indian Defense; Lasker Simul Special; Latvian Gambit; Lemming Defense;
Lion Defense; Marienbad System; Mexican Defense; Mikenas Defense; Modern Defense;
Montevideo Defense; Neo-Grünfeld Defense; Nimzo-Indian Defense;
Nimzowitsch Defense; Old Indian Defense; Owen Defense; Petrov's Defense;
Philidor Defense; Pirc Defense; Polish Defense; Pseudo Queen's Indian Defense;
Pterodactyl Defense; Queen's Indian Accelerated; Queen's Indian Defense; Rat Defense; Robatsch Defense;
Scandinavian Defense; Semi-Slav Defense; Sicilian Defense; Slav Defense; Slav Indian; St. George Defense; Tarrasch Defense;
Vulture Defense; Wade Defense; Ware Defense; Zaire Defense; Zukertort Defense
"""
BOTH = "Four Knights Game"


def _names(block):
    return {n.strip() for n in block.replace("\n", " ").split(";") if n.strip()}


assert not _names(WHITE) & _names(BLACK), "opening listed for both sides"
FAMILY_SIDE = {**{f: "white" for f in _names(WHITE)},
               **{f: "black" for f in _names(BLACK)},
               BOTH: "both"}


def split_name(name):
    if ":" in name:
        fam, rest = (s.strip() for s in name.split(":", 1))
    else:
        fam, rest = name.strip(), ""
    qualifier = ""
    if fam == "Queen's Pawn, Mengarini Attack":      # only name spelled this way
        fam, rest = "Queen's Pawn Game", "Mengarini Attack"
    elif ", " in fam:                                # "London System, with Bd3"
        fam, qualifier = (s.strip() for s in fam.split(",", 1))
    parts = [p.strip() for p in rest.split(",")] if rest else []
    variation = parts[0] if parts else ""
    sub = ", ".join(parts[1:])
    return fam, qualifier, variation, sub


def main():
    df = pd.read_csv(os.path.join(HERE, "lichess_openings.tsv"), sep="\t")
    rows = []
    for r in df.itertuples(index=False):
        fam, qual, var, sub = split_name(r.name)
        sans = [t for t in r.pgn.split() if not re.match(r"^\d+\.", t)]
        n = len(sans)
        base = re.sub(r" (Accepted|Declined)$", "", fam)
        rows.append({
            "eco": r.eco, "eco_letter": r.eco[0], "eco_group": ECO_GROUP[r.eco[0]],
            "family": fam, "family_qualifier": qual, "variation": var, "subvariation": sub,
            "base_opening": base, "family_side": FAMILY_SIDE.get(base),
            "plies": n, "white_moves": (n + 1) // 2, "black_moves": n // 2,
            "last_mover": "white" if n % 2 else "black",
            "name": r.name, "pgn": r.pgn,
        })
    out = pd.DataFrame(rows)

    missing = sorted(set(out.base_opening) - set(FAMILY_SIDE))
    unused = sorted(set(FAMILY_SIDE) - set(out.base_opening))
    assert not missing, f"base openings without a side: {missing}"
    assert not unused, f"side given for unknown base openings: {unused}"
    assert len(out) == len(df)

    ev_path = os.path.join(HERE, "family_side_evidence.csv")
    if os.path.exists(ev_path):
        ev = pd.read_csv(ev_path)[["family", "side_in_games", "side_ratio", "n_games"]]
        out = out.merge(ev, on="family", how="left")
        out["n_games"] = out.n_games.astype("Int64")

    out.to_csv(os.path.join(HERE, "lichess_openings_classified.csv"), index=False)
    print(f"{len(out)} lines, {out.family.nunique()} families -> "
          "openings/lichess_openings_classified.csv")


if __name__ == "__main__":
    main()
