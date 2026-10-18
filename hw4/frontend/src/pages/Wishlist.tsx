import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { PawIcon } from "../components/PawButton";
import { Product, fetchProducts } from "../api";
import { useAuth } from "../AuthContext";
import { useWishlist } from "../WishlistContext";

export default function Wishlist() {
  const { user, ready } = useAuth();
  const { ids } = useWishlist();
  const [products, setProducts] = useState<Product[] | null>(null);

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]));
  }, []);

  if (ready && !user) {
    return (
      <section className="page narrow center">
        <PawIcon className="wishlist-hero-paw" />
        <p className="eyebrow">Your Wishlist</p>
        <h1 className="display">Log in to see your wishlist.</h1>
        <p className="lede">Save favorites with the paw print on any product, and they'll wait for you here.</p>
        <Link to="/login" state={{ from: "/wishlist" }} className="btn">Log in</Link>
      </section>
    );
  }

  const byId = new Map((products ?? []).map((p) => [p.product_id, p]));
  const saved = ids.map((id) => byId.get(id)).filter((p): p is Product => Boolean(p));

  return (
    <section className="page">
      <header className="catalogue-head">
        <p className="eyebrow">Your Wishlist</p>
        <h1 className="display">
          {user?.first_name ? `${user.first_name}'s wishlist` : "Your wishlist"}
        </h1>
        <p className="lede">
          {saved.length > 0
            ? "Things you've had your eye on. Tap the paw again to let one go."
            : "Nothing saved yet. Tap the paw print on anything that catches your eye."}
        </p>
      </header>
      {products === null ? (
        <div className="grid" aria-busy="true">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="card card-skeleton" />
          ))}
        </div>
      ) : saved.length === 0 ? (
        <Link to="/products" className="btn">Browse the catalogue</Link>
      ) : (
        <div className="grid">
          {saved.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      )}
    </section>
  );
}
