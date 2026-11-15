import { createContext, useContext } from "react";
import type { Family } from "./catalog";
import type { OpeningLine, Repertoire } from "./practiceApi";
import type { LessonProgress } from "./progress";

export type Route = { view: "home" | "learn" | "family" | "lesson" | "review" | "repertoire" | "settings"; arg?: string };

/** Everything the pages share: the catalog, the player's repertoire and the actions that start practice. */
export type AppData = {
  catalog: OpeningLine[];
  families: Family[];
  variants: Map<number, string>;
  lineById: Map<number, OpeningLine>;
  repertoire: Repertoire | null;
  progress: Record<string, LessonProgress>;
  now: number;
  dueCount: number;
  go: (hash: string) => void;
  showToast: (text: string) => void;
  startLearning: (lineId: number, options?: { restart?: boolean }) => Promise<void>;
  startReview: (lineId?: number) => Promise<void>;
  refreshRepertoire: () => Promise<void>;
  markLearned: (lineId: number) => void;
};

export const AppContext = createContext<AppData | null>(null);
export function useApp() {
  const data = useContext(AppContext);
  if (!data) throw new Error("useApp needs AppContext");
  return data;
}
