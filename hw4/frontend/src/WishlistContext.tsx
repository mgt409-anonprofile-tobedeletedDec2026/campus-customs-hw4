import { ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react";
import { useAuth } from "./AuthContext";

interface WishlistState {
  ids: string[];
  has: (productId: string) => boolean;
  toggle: (productId: string) => Promise<void>;
}

const WishlistContext = createContext<WishlistState | null>(null);

async function wishlistRequest(method: string, path = ""): Promise<string[]> {
  const res = await fetch(`/api/wishlist${path}`, { method });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Couldn't update your wishlist.");
  return data.product_ids as string[];
}

/** The logged-in shopper's saved items. Guests have an empty wishlist. */
export function WishlistProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [ids, setIds] = useState<string[]>([]);

  useEffect(() => {
    if (!user) {
      setIds([]);
      return;
    }
    wishlistRequest("GET").then(setIds).catch(() => setIds([]));
  }, [user]);

  const toggle = useCallback(
    async (productId: string) => {
      const saved = ids.includes(productId);
      // Update right away so the paw responds instantly; roll back if the server says no.
      setIds((cur) => (saved ? cur.filter((id) => id !== productId) : [productId, ...cur]));
      try {
        setIds(await wishlistRequest(saved ? "DELETE" : "POST", `/${encodeURIComponent(productId)}`));
      } catch {
        setIds((cur) => (saved ? [productId, ...cur] : cur.filter((id) => id !== productId)));
      }
    },
    [ids],
  );

  return (
    <WishlistContext.Provider value={{ ids, has: (id) => ids.includes(id), toggle }}>
      {children}
    </WishlistContext.Provider>
  );
}

export function useWishlist() {
  const ctx = useContext(WishlistContext);
  if (!ctx) throw new Error("useWishlist must be used inside WishlistProvider");
  return ctx;
}
