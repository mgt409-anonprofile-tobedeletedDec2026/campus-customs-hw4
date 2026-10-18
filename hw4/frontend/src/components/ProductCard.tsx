import { CSSProperties, useRef } from "react";
import { Link } from "react-router-dom";
import { Product, formatPrice } from "../api";
import { useReveal } from "../useReveal";
import PawButton from "./PawButton";

const SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"];

/** "Available in S, M, L, XL and XXL" for the quick look. */
export function availabilityText(p: Product): string {
  const available = SIZE_ORDER.filter((s) => !p.sizes_sold_out.includes(s));
  if (available.length === 0) return "Currently sold out";
  if (available.length === SIZE_ORDER.length) return "Available in every size, XS to XXL";
  const list =
    available.length === 1 ? available[0] : `${available.slice(0, -1).join(", ")} and ${available[available.length - 1]}`;
  return `Available in ${list}`;
}

export default function ProductCard({ product, index }: { product: Product; index?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const reveal = useReveal(ref);
  // Stagger neighbours in a row slightly so a grid settles in like turning a page.
  const style = { "--reveal-delay": `${((index ?? 0) % 4) * 70}ms` } as CSSProperties;
  const availability = availabilityText(product);

  return (
    <div ref={ref} className={`card-wrap ${reveal}`} style={style}>
      <Link to={`/products/${product.product_id}`} className="card" aria-label={`${product.name}, ${availability}`}>
        <div className="card-frame">
          <img src={product.image_url} alt={product.name} loading="lazy" />
          <span className="quick-look" aria-hidden="true">
            <span className="quick-look-label">Quick look</span>
            {availability}
          </span>
        </div>
        <div className="card-body">
          {index !== undefined && <p className="card-no">No. {String(index + 1).padStart(3, "0")}</p>}
          <h3 className="card-name">{product.name}</h3>
          <p className="card-tagline">{product.tagline || product.description}</p>
          <p className="card-price">{formatPrice(product.price)}</p>
          <p className="card-sizes">{availability}</p>
        </div>
      </Link>
      {/* Outside the link so the paw never opens the product page by accident. */}
      <PawButton productId={product.product_id} productName={product.name} />
    </div>
  );
}
