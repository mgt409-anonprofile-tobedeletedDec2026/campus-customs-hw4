import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { useCart } from "../CartContext";
import { useWishlist } from "../WishlistContext";
import { PawIcon } from "./PawButton";

const links = [
  { to: "/", label: "Home", end: true },
  { to: "/products", label: "Products" },
  { to: "/about", label: "About Us" },
];

export default function Nav() {
  const [open, setOpen] = useState(false);
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { user, ready, logout } = useAuth();
  const { bag } = useCart();
  const { ids: wishlistIds } = useWishlist();
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header className="site-header">
      <div className="ticker">
        <span>New Haven, Connecticut</span>
        <span className="ticker-dot" aria-hidden="true">✦</span>
        <span>Outfitting Elis since before you could spell Boola</span>
      </div>
      <nav className="nav" aria-label="Main">
        <Link to="/" className="wordmark" aria-label="Campus Customs home">
          <span className="wordmark-name">Campus Customs</span>
          <span className="wordmark-sub">Purveyors of Bulldog Blue</span>
        </Link>
        <button
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="nav-links"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="sr-only">Menu</span>
          <span className="nav-toggle-bar" />
          <span className="nav-toggle-bar" />
        </button>
        <div id="nav-links" className={`nav-links${open ? " is-open" : ""}`}>
          {links.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className="nav-link">
              {l.label}
            </NavLink>
          ))}
          <span className="nav-divider" aria-hidden="true" />
          {ready && user ? (
            <>
              <span className="nav-greeting">Hi, {user.first_name}</span>
              <NavLink
                to="/wishlist"
                className="nav-link nav-bag nav-wishlist"
                aria-label={`Wishlist, ${wishlistIds.length} items`}
                title="Wishlist"
              >
                <PawIcon />
                {wishlistIds.length > 0 && <span className="bag-count">{wishlistIds.length}</span>}
              </NavLink>
              <NavLink to="/bag" className="nav-link nav-bag" aria-label={`Bag, ${bag.count} items`}>
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 8h14l-1.2 12H6.2L5 8Z" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
                  <path d="M9 8V6.5a3 3 0 0 1 6 0V8" fill="none" stroke="currentColor" strokeWidth="1.6" />
                </svg>
                Bag
                {bag.count > 0 && <span className="bag-count">{bag.count}</span>}
              </NavLink>
              <button
                className="nav-cta"
                onClick={async () => {
                  await logout();
                  navigate("/");
                }}
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="nav-link">Log in</NavLink>
              <NavLink to="/create-account" className="nav-cta">Create account</NavLink>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
