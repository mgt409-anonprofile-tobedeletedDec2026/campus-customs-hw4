import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import ProductCard from "./ProductCard";
import { usePicks } from "../PicksContext";

function PawPrint({ className = "" }: { className?: string }) {
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

function Bone({ className = "" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 24" aria-hidden="true">
      <rect x="9" y="8" width="46" height="8" rx="3" />
      <circle cx="9" cy="7" r="5" />
      <circle cx="9" cy="17" r="5" />
      <circle cx="55" cy="7" r="5" />
      <circle cx="55" cy="17" r="5" />
    </svg>
  );
}

/** Handsome Dan's latest search results, laid out on whatever page the shopper is on. */
export default function DanPicks() {
  const { picks, version, clearPicks } = usePicks();
  const { pathname } = useLocation();
  const sectionRef = useRef<HTMLElement>(null);
  const [collapsed, setCollapsed] = useState(false);

  // New picks open fully and scroll into view, without leaving the page.
  useEffect(() => {
    if (picks && version > 0) {
      setCollapsed(false);
      sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [version]); // eslint-disable-line react-hooks/exhaustive-deps

  // Moving to another page (e.g. clicking a pick) tucks the picks into a slim bar
  // so the new page's content comes first.
  useEffect(() => {
    setCollapsed(true);
  }, [pathname]);

  if (!picks) return null;

  if (collapsed) {
    return (
      <section className="dan-picks dan-picks-collapsed" aria-label="Handsome Dan's Picks">
        <div className="dan-picks-bar">
          <Bone className="bone" />
          <span>
            Handsome Dan&rsquo;s Picks: <strong>{picks.label}</strong> &middot; {picks.products.length}{" "}
            {picks.products.length === 1 ? "piece" : "pieces"}
          </span>
          <button type="button" className="link-btn dan-picks-show" onClick={() => setCollapsed(false)}>
            Show picks
          </button>
          <button type="button" className="link-btn" onClick={clearPicks}>
            Clear
          </button>
        </div>
      </section>
    );
  }

  return (
    <section key={version} ref={sectionRef} className="dan-picks" aria-label="Handsome Dan's Picks">
      <div className="dan-picks-inner">
        <PawPrint className="paw paw-1" />
        <PawPrint className="paw paw-2" />
        <PawPrint className="paw paw-3" />
        <header className="dan-picks-head">
          <div>
            <p className="eyebrow dan-picks-eyebrow">
              <Bone className="bone" /> Handsome Dan&rsquo;s Picks
            </p>
            <h2 className="dan-picks-title">{picks.label}</h2>
            <p className="dan-picks-count">
              {picks.products.length} {picks.products.length === 1 ? "piece" : "pieces"} fetched from the stockroom
            </p>
          </div>
          <div className="dan-picks-actions">
            <button type="button" className="link-btn" onClick={() => setCollapsed(true)}>
              Hide
            </button>
            <button type="button" className="btn btn-ghost dan-picks-clear" onClick={clearPicks}>
              Clear picks
            </button>
          </div>
        </header>
        <div className="grid dan-picks-grid">
          {picks.products.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </div>
    </section>
  );
}
