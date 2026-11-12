export type OpeningLine = {
  id: string;
  name: string;
  description: string;
  moves: string[];
  previewPly: number;
  explanations: string[];
};

// Small frontend-only catalog. The backend will eventually supply opening lines.
export const openingLines: OpeningLine[] = [
  {
    id: "ruy-lopez", name: "Ruy López Opening", previewPly: 5,
    description: "Develop with purpose and put pressure on the centre.",
    moves: ["e4", "e5", "Nf3", "Nc6", "Bb5", "a6", "Ba4", "Nf6", "O-O"],
    explanations: [
      "Claim space in the centre and open a path for your bishop.",
      "Develop your knight and attack the pawn on e5.",
      "Bring your bishop to b5, putting pressure on the knight that defends e5.",
      "Keep your bishop active by moving it back to a4.",
      "Castle kingside to protect your king and bring the rook into play.",
    ],
  },
  {
    id: "italian-game", name: "Italian Game", previewPly: 5,
    description: "Bring your pieces out and build a strong centre.",
    moves: ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "c3", "Nf6", "d4", "exd4", "cxd4"],
    explanations: [
      "Take space in the centre with your king's pawn.",
      "Develop your knight towards the centre and attack e5.",
      "Place your bishop on c4, looking towards Black's f7 pawn.",
      "Support a future d4 push with your c-pawn.",
      "Challenge the centre with d4, supported by your c3 pawn.",
      "Recapture with the c-pawn to keep two pawns in the centre.",
    ],
  },
  {
    id: "scotch-game", name: "Scotch Game", previewPly: 5,
    description: "Open the centre early and give your pieces room.",
    moves: ["e4", "e5", "Nf3", "Nc6", "d4", "exd4", "Nxd4", "Nf6", "Nc3"],
    explanations: [
      "Start by claiming central space with e4.",
      "Develop your knight and put pressure on e5.",
      "Open the centre with a direct d4 pawn push.",
      "Recapture on d4 with your knight, placing it in the centre.",
      "Develop your other knight to c3 to support the centre.",
    ],
  },
];
