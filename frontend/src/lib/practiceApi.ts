export const sides = ["white", "black", "both"] as const;
export type Side = typeof sides[number];
export const sideLabels: Record<Side, string> = { white: "White", black: "Black", both: "Both" };

export type OpeningLine = {
  line_id: number;
  opening_family: string;
  name: string;
  eco: string;
  moves_uci: string;
  learned: boolean;
};

export type Session = {
  status: "choose_side" | "play" | "complete";
  session_id: string;
  line_id: number;
  name: string;
  side: Side | null;
  available_sides: Side[];
  move_index: number;
  total_plies: number;
  played_moves: string[];
  hint: string | null;
  correct?: boolean;
  fsrs_rating?: string | null;
};

export type ReviewStart = Session | { status: "learn_first" | "none_due" };

export async function practiceRequest<T>(path: string, fields: object = {}, signal?: AbortSignal): Promise<T> {
  let playerId = localStorage.getItem("tempo-player");
  if (!playerId) {
    playerId = crypto.randomUUID();
    localStorage.setItem("tempo-player", playerId);
  }
  const response = await fetch("/api/" + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_id: playerId, ...fields }),
    signal,
  });
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("Cannot reach TEMPO. Start the Python backend and try again.");
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "The request failed.");
  return result;
}
