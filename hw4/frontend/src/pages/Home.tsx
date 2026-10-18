import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { COLLECTIONS, Product, fetchProducts, formatPrice } from "../api";
import Skyline from "../components/Skyline";

const FEATURED = [
  "brooks-brothers-bomber-jacket-yale",
  "yale-bowl-t-shirt",
  "district-vit-hoodie-vintage-sailor-bulldog",
  "poly-twill-crewneck-arched-yale",
];
const NUMERALS = ["I", "II", "III", "IV"];

export default function Home() {
  const [products, setProducts] = useState<Product[]>([]);

  useEffect(() => {
    fetchProducts().then(setProducts).catch(() => setProducts([]));
  }, []);

  const featured = FEATURED.map((id) => products.find((p) => p.product_id === id)).filter(
    (p): p is Product => Boolean(p),
  );

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">The Autumn Ledger &middot; New Haven</p>
          <h1 className="display">
            Blue is not a color here. <em>It is a culture.</em>
          </h1>
          <p className="lede">
            October on Old Campus. The elms have opinions. A wind comes up off the harbor and
            finds every weakness in a lesser sweatshirt. We have spent a long time thinking about
            that wind, and about what a person ought to be wearing when it arrives.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn">Browse the catalogue</Link>
            <Link to="/about" className="btn btn-ghost">Read our story</Link>
          </div>
        </div>
        <div className="hero-plates">
          {featured.slice(0, 3).map((p, i) => (
            <Link key={p.product_id} to={`/products/${p.product_id}`} className={`plate plate-${i + 1}`}>
              <img src={p.image_url} alt={p.name} />
              <span className="plate-caption">Plate {NUMERALS[i]}. {p.name}</span>
            </Link>
          ))}
        </div>
      </section>

      <div className="masthead" aria-hidden="true">
        <Skyline className="skyline" />
      </div>

      <section className="band">
        <blockquote className="pullquote">
          <p>
            &ldquo;We do not sell sweatshirts. We sell the feeling of walking up Hillhouse Avenue
            in November with somewhere important to be.&rdquo;
          </p>
          <cite>Overheard behind the counter</cite>
        </blockquote>
      </section>

      <section className="page">
        <div className="section-head">
          <p className="eyebrow">Four Ways In</p>
          <h2 className="section-title">The Collections</h2>
        </div>
        <div className="collections">
          {Object.entries(COLLECTIONS).map(([key, c], i) => (
            <Link key={key} to={`/products?collection=${key}`} className="collection">
              <span className="collection-no">{NUMERALS[i]}</span>
              <h3>{c.label}</h3>
              <p>{c.blurb}</p>
              <span className="collection-link">Explore &rarr;</span>
            </Link>
          ))}
        </div>
      </section>

      {featured.length > 0 && (
        <section className="page">
          <div className="section-head">
            <p className="eyebrow">From the Ledger</p>
            <h2 className="section-title">Things we can&rsquo;t stop talking about</h2>
          </div>
          <div className="featured">
            {featured.map((p) => (
              <Link key={p.product_id} to={`/products/${p.product_id}`} className="featured-item">
                <div className="featured-img">
                  <img src={p.image_url} alt={p.name} loading="lazy" />
                </div>
                <h3>{p.name}</h3>
                <p className="featured-tagline">{p.tagline}</p>
                <p className="card-price">{formatPrice(p.price)}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="page">
        <div className="dan-intro">
          <p className="eyebrow">At Your Service</p>
          <h2 className="section-title">Ask Handsome Dan.</h2>
          <p>
            Our bulldog keeps the stockroom ledger in his head and does not exaggerate. Sizes,
            prices, what&rsquo;s left on the shelf. Find him in the bottom right corner of every
            page. He doesn&rsquo;t bite. Much.
          </p>
        </div>
      </section>
    </>
  );
}
