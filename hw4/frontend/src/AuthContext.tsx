import { ReactNode, createContext, useContext, useEffect, useState } from "react";
import { User, fetchMe, logout as apiLogout } from "./api";
import { clearRecent } from "./recentlyViewed";

interface AuthState {
  user: User | null;
  ready: boolean;
  setUser: (user: User | null) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    fetchMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, []);

  async function logout() {
    await apiLogout().catch(() => undefined);
    clearRecent(); // don't leave browsing history behind on a shared computer
    setUser(null);
  }

  return <AuthContext.Provider value={{ user, ready, setUser, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
