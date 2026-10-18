import { MouseEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { useWishlist } from "../WishlistContext";

export function PawIcon({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" aria-hidden="true">
      <ellipse cx="16" cy="21" rx="7" ry="6" />
      <ellipse cx="7" cy="13" rx="3" ry="4" />
      <ellipse cx="12.5" cy="7.5" rx="3" ry="4" />
      <ellipse cx="19.5" cy="7.5" rx="3" ry="4" />
      <ellipse cx="25" cy="13" rx="3" ry="4" />
    </svg>
  );
}

/** Paw-print toggle that saves a product to the shopper's wishlist. */
export default function PawButton({
  productId,
  productName,
  size = "sm",
}: {
  productId: string;
  productName: string;
  size?: "sm" | "lg";
}) {
  const { user } = useAuth();
  const { has, toggle } = useWishlist();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const saved = has(productId);
  const [stamping, setStamping] = useState(false);
  const tip = !user ? "Log in to save to Wishlist" : saved ? "Saved to Wishlist" : "Save to Wishlist";

  function handleClick(e: MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!user) {
      navigate("/login", { state: { from: pathname } });
      return;
    }
    if (!saved) setStamping(true); // a little ink-stamp when an item is saved
    toggle(productId);
  }

  return (
    <button
      type="button"
      className={`paw-btn paw-btn-${size}${saved ? " is-saved" : ""}${stamping ? " is-stamping" : ""}`}
      onAnimationEnd={() => setStamping(false)}
      onClick={handleClick}
      aria-pressed={saved}
      aria-label={`${tip}: ${productName}`}
      data-tip={tip}
    >
      <PawIcon />
      {size === "lg" && <span>{saved ? "Saved to Wishlist" : "Save to Wishlist"}</span>}
    </button>
  );
}
