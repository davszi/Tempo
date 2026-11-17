import { createContext, useContext } from "react";
import type { OpeningSort, Family, OpeningType } from "./catalog";
import type { OpeningLine, Repertoire } from "./practiceApi";
import type { LessonProgress } from "./progress";
import type { Account } from "./auth";

export type LearningSide = "all" | "white" | "black";
export const learningSideKey = "tempo-learning-side";

export type Route = { view: "home" | "learn" | "family" | "lesson" | "review" | "repertoire" | "settings" | "login" | "signup" | "forgot-password" | "reset-password"; arg?: string };

/** Everything the pages share: the catalog, the player's repertoire and the actions that start practice. */
export type AppData = {
  catalog: OpeningLine[];
  families: Family[];
  openingSort: OpeningSort;
  setOpeningSort: (band: OpeningSort) => void;
  selectedOpeningTypes: OpeningType[];
  setSelectedOpeningTypes: (types: OpeningType[]) => void;
  availableOpeningTypes: OpeningType[];
  learningSide: LearningSide;
  setLearningSide: (side: LearningSide) => void;
  variants: Map<number, string>;
  lineById: Map<number, OpeningLine>;
  repertoire: Repertoire | null;
  progress: Record<string, LessonProgress>;
  now: number;
  dueCount: number;
  go: (hash: string) => void;
  showToast: (text: string) => void;
  startLearning: (lineId: number, options?: { restart?: boolean; replayFrom?: number; withoutHints?: boolean }) => Promise<void>;
  startReview: (lineId?: number) => Promise<void>;
  refreshRepertoire: () => Promise<Repertoire | undefined>;
  markLearned: (lineId: number) => void;
  /** The signed-in account, or null for a guest. */
  account: Account | null;
  signOut: () => Promise<void>;
  /** Show updated profile details after an edit. */
  accountChanged: (user: Account) => void;
  /** Leave the app after the account was deleted. */
  accountDeleted: () => Promise<void>;
};

export const AppContext = createContext<AppData | null>(null);
export function useApp() {
  const data = useContext(AppContext);
  if (!data) throw new Error("useApp needs AppContext");
  return data;
}
