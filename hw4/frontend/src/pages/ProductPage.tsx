import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { ProductDetail, fetchProduct, formatPrice } from "../api";
import { useAuth } from "../AuthContext";
import { useCart } from "../CartContext";
import { recordView } from "../recentlyViewed";
import PawButton from "../components/PawButton";

const LOW_STOCK = 5;
const MAX_PER_LINE = 10;

export default function ProductPage() {
  const { productId = "" } = useParams();
  const location = useLocation();
  const { user } = useAuth();
  const { bag, add } = useCart();
  const [product, setProduct] = useState<ProductDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [size, setSize] = useState<string | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [adding, setAdding] = useState(false);
  const [message, setMessage] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  useEffect(() => {
    setProduct(null);
    setError(null);
    setSize(null);
    setQuantity(1);
    setMessage(null);
    fetchProduct(productId)
      .then((p) => {
        setProduct(p);
        recordView({ product_id: p.product_id, name: p.name, price: p.price, image_url: p.image_url });
      })
      .catch((e: Error) => setError(e.message));
  }, [productId]);

  if (error) {
    return (
      <section className="page narrow center">
        <p className="eyebrow">{error === "not-found" ? "Not in the ledger" : "Something went wrong"}</p>
        <h1 className="display">
          {error === "not-found" ? "We can't find that piece." : "The stockroom isn't answering."}
        </h1>
        <Link to="/products" className="btn">Back to the catalogue</Link>
      </section>
    );
  }

  if (!product) {
    return (
      <section className="page product" aria-busy="true">
        <div className="product-media skeleton-block" />
        <div className="product-info">
          <div className="skeleton-line wide" />
          <div className="skeleton-line" />
          <div className="skeleton-line" />
        </div>
      </section>
    );
  }

  const soldOutSizes = product.sizes.filter((s) => s.quantity === 0).map((s) => s.size);
  const allSoldOut = product.sizes.length > 0 && soldOutSizes.length === product.sizes.length;

  const stock = product.sizes.find((s) => s.size === size)?.quantity ?? 0;
  const alreadyInBag =
    bag.items.find((i) => i.product_id === product.product_id && i.size === size)?.quantity ?? 0;
  const maxAddable = Math.max(0, Math.min(stock, MAX_PER_LINE) - alreadyInBag);

  function chooseSize(s: string) {
    setSize(s);
    setQuantity(1);
    setMessage(null);
  }

  async function handleAdd() {
    if (!product || !size) return;
    setAdding(true);
    setMessage(null);
    try {
      await add(product.product_id, size, quantity);
      setMessage({ kind: "ok", text: `Added ${quantity} × size ${size} to your bag.` });
      setQuantity(1);
    } catch (e) {
      setMessage({ kind: "error", text: (e as Error).message });
    } finally {
      setAdding(false);
    }
  }

  return (
    <section className="page">
      <Link to="/products" className="back-link">&larr; The Catalogue</Link>
      <div className="product">
        <div className="product-media">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="product-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1 className="product-name">{product.name}</h1>
          <div className="product-price-row">
            <p className="product-price">{formatPrice(product.price)}</p>
            <PawButton productId={product.product_id} productName={product.name} size="lg" />
          </div>

          {product.story && <p className="product-story">{product.story}</p>}

          <div className="particulars">
            <h2>The Particulars</h2>
            <p>{product.description}</p>
            {product.colors.length > 0 && (
              <p className="colors">
                <span>Colors:</span> {product.colors.join(", ")}
              </p>
            )}
          </div>

          <div className="sizes">
            <h2 id="size-heading">Sizes &amp; Stock</h2>
            <div className="size-grid" role="group" aria-labelledby="size-heading">
              {product.sizes.map((s) => {
                const out = s.quantity === 0;
                const selected = size === s.size;
                return (
                  <button
                    key={s.size}
                    type="button"
                    className={`size${out ? " is-out" : ""}${selected ? " is-selected" : ""}`}
                    disabled={out}
                    aria-pressed={selected}
                    onClick={() => chooseSize(s.size)}
                  >
                    <span className="size-label">{s.size}</span>
                    <span className="size-qty">
                      {out ? "Sold out" : s.quantity <= LOW_STOCK ? `Only ${s.quantity} left` : `${s.quantity} in stock`}
                    </span>
                    {out && <span className="size-stamp" aria-hidden="true">Sold Out</span>}
                  </button>
                );
              })}
            </div>

            {!allSoldOut && (
              <div className="buy-box">
                {user ? (
                  <>
                    <div className="buy-row">
                      <div className="stepper" aria-label="Quantity">
                        <button
                          type="button"
                          onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                          disabled={!size || quantity <= 1}
                          aria-label="Decrease quantity"
                        >
                          &minus;
                        </button>
                        <span aria-live="polite">{quantity}</span>
                        <button
                          type="button"
                          onClick={() => setQuantity((q) => Math.min(maxAddable, q + 1))}
                          disabled={!size || quantity >= maxAddable}
                          aria-label="Increase quantity"
                        >
                          +
                        </button>
                      </div>
                      <button
                        type="button"
                        className="btn btn-add"
                        onClick={handleAdd}
                        disabled={!size || adding || maxAddable === 0}
                      >
                        {adding ? "Adding..." : size ? "Add to bag" : "Choose a size"}
                      </button>
                    </div>
                    {size && maxAddable === 0 && (
                      <p className="buy-note">You already have every available {size} in your bag.</p>
                    )}
                    {message && (
                      <p className={`notice${message.kind === "error" ? " notice-error" : ""}`} role="status">
                        {message.text}
                        {message.kind === "ok" && (
                          <>
                            {" "}
                            <Link to="/bag">View bag &rarr;</Link>
                          </>
                        )}
                      </p>
                    )}
                  </>
                ) : (
                  <Link to="/login" state={{ from: location.pathname }} className="btn btn-add btn-ghost">
                    Log in to shop
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
