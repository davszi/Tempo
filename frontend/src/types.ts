export type Page = "dashboard" | "openings" | "practice" | "planner" | "settings";
export type Opening = { id: string; name: string };
export type OpeningProgress = {
  status: "new" | "learning" | "completed";
  nextReview?: string;
};
export type UserProgress = Record<string, OpeningProgress>;
