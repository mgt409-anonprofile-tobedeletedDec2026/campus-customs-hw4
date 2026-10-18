import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { formatPrice } from "../api";
import { RECENT_EVENT, RecentItem, clearRecent, getRecent } from "../recentlyViewed";

/** A strip above the footer so shoppers can hop back to products they looked at. */
export default function RecentlyViewed() {
  const { pathname } = useLocation();
  const [items, setItems] = useState<RecentItem[]>(getRecent);

  useEffect(() => {
    const refresh = () => setItems(getRecent());
    window.addEventListener(RECENT_EVENT, refresh);
    window.addEventListener("storage", refresh);
    return () => {
      window.removeEventListener(RECENT_EVENT, refresh);
      window.removeEventListener("storage", refresh);
    };
  }, []);

  const currentId = pathname.match(/^\/products\/([^/]+)/)?.[1];
  const shown = items.filter((i) => i.product_id !== currentId);
  if (shown.length === 0) return null;

  return (
    <section className="recent" aria-label="Recently viewed">
      <div className="recent-inner">
        <header className="recent-head">
          <h2>Recently viewed</h2>
          <button type="button" className="link-btn" onClick={clearRecent}>Clear</button>
        </header>
        <ul className="recent-list">
          {shown.map((i) => (
            <li key={i.product_id}>
              <Link to={`/products/${i.product_id}`} className="recent-card">
                <img src={i.image_url} alt="" loading="lazy" />
                <span className="recent-name">{i.name}</span>
                <span className="recent-price">{formatPrice(i.price)}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
