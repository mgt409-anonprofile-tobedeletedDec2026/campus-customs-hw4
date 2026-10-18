import { ReactNode, createContext, useCallback, useContext, useEffect, useState } from "react";
import { Bag, addToBag, fetchBag, removeBagItem, updateBagItem } from "./api";
import { useAuth } from "./AuthContext";

const EMPTY: Bag = { items: [], count: 0, subtotal: 0 };

interface CartState {
  bag: Bag;
  add: (productId: string, size: string, quantity: number) => Promise<void>;
  update: (itemId: number, quantity: number) => Promise<void>;
  remove: (itemId: number) => Promise<void>;
}

const CartContext = createContext<CartState | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [bag, setBag] = useState<Bag>(EMPTY);

  // Load the bag whenever someone logs in; clear it when they log out.
  useEffect(() => {
    if (!user) {
      setBag(EMPTY);
      return;
    }
    fetchBag().then(setBag).catch(() => setBag(EMPTY));
  }, [user]);

  const add = useCallback(async (productId: string, size: string, quantity: number) => {
    setBag(await addToBag(productId, size, quantity));
  }, []);
  const update = useCallback(async (itemId: number, quantity: number) => {
    setBag(await updateBagItem(itemId, quantity));
  }, []);
  const remove = useCallback(async (itemId: number) => {
    setBag(await removeBagItem(itemId));
  }, []);

  return <CartContext.Provider value={{ bag, add, update, remove }}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart must be used inside CartProvider");
  return ctx;
}
