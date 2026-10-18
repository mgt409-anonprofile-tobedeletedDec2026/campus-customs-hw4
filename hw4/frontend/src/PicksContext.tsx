import { ReactNode, createContext, useContext, useState } from "react";
import { PagePicks } from "./api";

interface PicksState {
  picks: PagePicks | null;
  /** Bumps on every new set of picks so the section can replay its slide-in. */
  version: number;
  showPicks: (picks: PagePicks) => void;
  clearPicks: () => void;
}

const PicksContext = createContext<PicksState | null>(null);

/** Holds Handsome Dan's latest search results so any page can show them. */
export function PicksProvider({ children }: { children: ReactNode }) {
  const [picks, setPicks] = useState<PagePicks | null>(null);
  const [version, setVersion] = useState(0);

  function showPicks(next: PagePicks) {
    setPicks(next);
    setVersion((v) => v + 1);
  }

  return (
    <PicksContext.Provider value={{ picks, version, showPicks, clearPicks: () => setPicks(null) }}>
      {children}
    </PicksContext.Provider>
  );
}

export function usePicks() {
  const ctx = useContext(PicksContext);
  if (!ctx) throw new Error("usePicks must be used inside PicksProvider");
  return ctx;
}
