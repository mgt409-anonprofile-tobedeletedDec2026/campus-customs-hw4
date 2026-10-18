import { useState } from "react";
import { Link } from "react-router-dom";
import { formatPrice } from "../api";
import { useAuth } from "../AuthContext";
import { useCart } from "../CartContext";

const MAX_PER_LINE = 10;

export default function Bag() {
  const { user, ready } = useAuth();
  const { bag, update, remove } = useCart();
  const [error, setError] = useState("");

  async function run(action: () => Promise<void>) {
    setError("");
    try {
      await action();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  if (ready && !user) {
    return (
      <section className="page narrow center">
        <p className="eyebrow">Your Bag</p>
        <h1 className="display">Log in to see your bag.</h1>
        <Link to="/login" state={{ from: "/bag" }} className="btn">Log in</Link>
      </section>
    );
  }

  if (bag.items.length === 0) {
    return (
      <section className="page narrow center">
        <p className="eyebrow">Your Bag</p>
        <h1 className="display">Empty, for now.</h1>
        <p className="lede">
          A bag with nothing in it is just a promise. The catalogue is right this way.
        </p>
        <Link to="/products" className="btn">Browse the catalogue</Link>
      </section>
    );
  }

  return (
    <section className="page">
      <header className="catalogue-head">
        <p className="eyebrow">Your Bag</p>
        <h1 className="display">
          {user?.first_name ? `${user.first_name}'s selections` : "Your selections"}
        </h1>
      </header>

      {error && <p className="notice notice-error" role="alert">{error}</p>}

      <div className="bag">
        <ul className="bag-items">
          {bag.items.map((item) => {
            const max = Math.min(item.in_stock, MAX_PER_LINE);
            return (
              <li key={item.id} className="bag-item">
                <Link to={`/products/${item.product_id}`} className="bag-thumb">
                  <img src={item.image_url} alt={item.name} />
                </Link>
                <div className="bag-details">
                  <Link to={`/products/${item.product_id}`} className="bag-name">{item.name}</Link>
                  <p className="bag-meta">
                    Size {item.size} &middot; {formatPrice(item.price)} each
                  </p>
                  {item.quantity > item.in_stock && (
                    <p className="bag-warning">Only {item.in_stock} left in this size.</p>
                  )}
                  <div className="bag-actions">
                    <div className="stepper stepper-sm" aria-label={`Quantity of ${item.name}`}>
                      <button
                        type="button"
                        onClick={() => run(() => update(item.id, item.quantity - 1))}
                        aria-label="Decrease quantity"
                      >
                        &minus;
                      </button>
                      <span>{item.quantity}</span>
                      <button
                        type="button"
                        onClick={() => run(() => update(item.id, item.quantity + 1))}
                        disabled={item.quantity >= max}
                        aria-label="Increase quantity"
                      >
                        +
                      </button>
                    </div>
                    <button type="button" className="link-btn" onClick={() => run(() => remove(item.id))}>
                      Remove
                    </button>
                  </div>
                </div>
                <p className="bag-line-total">{formatPrice(item.line_total)}</p>
              </li>
            );
          })}
        </ul>

        <aside className="bag-summary" aria-label="Order summary">
          <h2>Summary</h2>
          <dl>
            <div>
              <dt>Items</dt>
              <dd>{bag.count}</dd>
            </div>
            <div>
              <dt>Subtotal</dt>
              <dd>{formatPrice(bag.subtotal)}</dd>
            </div>
            <div className="bag-fine">
              <dt>Shipping &amp; tax</dt>
              <dd>At checkout</dd>
            </div>
          </dl>
          <Link to="/checkout" className="btn btn-block">Check out</Link>
          <Link to="/products" className="bag-continue">Continue shopping</Link>
        </aside>
      </div>
    </section>
  );
}
