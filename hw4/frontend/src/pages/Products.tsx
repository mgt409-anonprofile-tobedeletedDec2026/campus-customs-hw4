import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { COLLECTIONS, COLOR_FAMILIES, Product, fetchProducts, garmentColor, garmentFamily } from "../api";

const FAMILIES = ["All", "Hoodies", "Crewnecks", "Quarter-zips", "Tees", "Outerwear", "Performance"];
const SIZES = ["XS", "S", "M", "L", "XL", "XXL"];
const PRICE_CAPS = [35, 50, 75];
const SORTS: Record<string, string> = {
  featured: "Featured",
  price_asc: "Price: low to high",
  price_desc: "Price: high to low",
  name: "Name: A to Z",
};
const SWATCHES: Record<string, string> = {
  Navy: "#1f2f4f",
  Gray: "#b9bdc4",
  Charcoal: "#4a4f57",
  Cream: "#efe6d2",
  White: "#ffffff",
  Pink: "#e7a08c",
};

export default function Products() {
  const [products, setProducts] = useState<Product[] | null>(null);
  const [error, setError] = useState(false);
  const [params, setParams] = useSearchParams();

  const family = params.get("family") ?? "All";
  const collectionKey = params.get("collection");
  const collection = collectionKey ? COLLECTIONS[collectionKey] : undefined;
  const query = params.get("q") ?? "";
  const sort = params.get("sort") ?? "featured";
  const maxPrice = Number(params.get("max")) || null;
  const color = params.get("color");
  const size = params.get("size");
  const hideSoldOut = params.get("instock") === "1";

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError(true));
  }, []);

  function update(key: string, value: string | null) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  function clearFilters() {
    setParams(new URLSearchParams(), { replace: true });
  }

  const visible = useMemo(() => {
    if (!products) return [];
    const q = query.trim().toLowerCase();
    const rows = products
      .map((p, i) => ({ p, number: i }))
      .filter(({ p }) => family === "All" || garmentFamily(p) === family)
      .filter(({ p }) => !collection || collection.match(p))
      .filter(({ p }) => !maxPrice || p.price <= maxPrice)
      .filter(({ p }) => !color || garmentColor(p) === color)
      .filter(({ p }) => !size || !p.sizes_sold_out.includes(size))
      .filter(({ p }) => !hideSoldOut || p.total_in_stock > 0)
      .filter(
        ({ p }) =>
          !q ||
          `${p.name} ${p.garment_type} ${p.description} ${p.colors.join(" ")}`.toLowerCase().includes(q),
      );
    if (sort === "price_asc") rows.sort((a, b) => a.p.price - b.p.price || a.number - b.number);
    if (sort === "price_desc") rows.sort((a, b) => b.p.price - a.p.price || a.number - b.number);
    if (sort === "name") rows.sort((a, b) => a.p.name.localeCompare(b.p.name));
    return rows;
  }, [products, family, collection, query, sort, maxPrice, color, size, hideSoldOut]);

  const activeCount =
    [family !== "All", collection, query, maxPrice, color, size, hideSoldOut].filter(Boolean).length +
    (sort !== "featured" ? 1 : 0);

  return (
    <section className="page">
      <header className="catalogue-head">
        <p className="eyebrow">Autumn Edition</p>
        <h1 className="display">The Catalogue</h1>
        <p className="lede">
          {collection
            ? collection.blurb
            : "Every piece we carry, photographed honestly and described with perhaps too much feeling."}
        </p>
      </header>

      <div className="filters">
        <div className="chips" role="group" aria-label="Filter by item type">
          {FAMILIES.map((f) => (
            <button
              key={f}
              className={`chip${family === f ? " is-active" : ""}`}
              aria-pressed={family === f}
              onClick={() => update("family", f === "All" ? null : f)}
            >
              {f}
            </button>
          ))}
        </div>
        <label className="search">
          <span className="sr-only">Search the catalogue</span>
          <input
            type="search"
            placeholder="Search the catalogue"
            value={query}
            onChange={(e) => update("q", e.target.value || null)}
          />
        </label>
      </div>

      <div className="refine" role="group" aria-label="Sort and refine">
        <label className="refine-field">
          <span>Sort</span>
          <select value={sort} onChange={(e) => update("sort", e.target.value === "featured" ? null : e.target.value)}>
            {Object.entries(SORTS).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </label>
        <label className="refine-field">
          <span>Price</span>
          <select value={maxPrice ?? ""} onChange={(e) => update("max", e.target.value || null)}>
            <option value="">Any price</option>
            {PRICE_CAPS.map((cap) => (
              <option key={cap} value={cap}>Under ${cap}</option>
            ))}
          </select>
        </label>
        <label className="refine-field">
          <span>In my size</span>
          <select value={size ?? ""} onChange={(e) => update("size", e.target.value || null)}>
            <option value="">Any size</option>
            {SIZES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <div className="refine-field">
          <span id="color-label">Color</span>
          <div className="swatches" role="group" aria-labelledby="color-label">
            {COLOR_FAMILIES.map((c) => (
              <button
                key={c}
                type="button"
                className={`swatch${color === c ? " is-active" : ""}`}
                style={{ background: SWATCHES[c] }}
                aria-pressed={color === c}
                aria-label={c}
                title={c}
                onClick={() => update("color", color === c ? null : c)}
              />
            ))}
          </div>
        </div>
        <label className="refine-check">
          <input type="checkbox" checked={hideSoldOut} onChange={(e) => update("instock", e.target.checked ? "1" : null)} />
          Hide sold-out items
        </label>
      </div>

      {collection && (
        <p className="active-collection">
          Showing <strong>{collection.label}</strong>
          <button onClick={() => update("collection", null)} aria-label="Clear collection">
            Clear &times;
          </button>
        </p>
      )}

      {error && (
        <div className="notice notice-error" role="alert">
          The stockroom isn&rsquo;t answering. Make sure the backend is running, then refresh.
        </div>
      )}

      {!products && !error && (
        <div className="grid" aria-busy="true" aria-label="Loading products">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="card card-skeleton" />
          ))}
        </div>
      )}

      {products && (
        <>
          <div className="result-bar">
            <p className="result-count" aria-live="polite">
              {visible.length} {visible.length === 1 ? "piece" : "pieces"}
              {color && <> &middot; {color}</>}
              {size && <> &middot; in stock in {size}</>}
            </p>
            {activeCount > 0 && (
              <button type="button" className="link-btn" onClick={clearFilters}>
                Clear all filters
              </button>
            )}
          </div>
          {visible.length === 0 ? (
            <div className="notice">Nothing matches all of that. Try loosening a filter, or ask Handsome Dan.</div>
          ) : (
            <div className="grid">
              {visible.map(({ p, number }) => (
                <ProductCard key={p.product_id} product={p} index={number} />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
