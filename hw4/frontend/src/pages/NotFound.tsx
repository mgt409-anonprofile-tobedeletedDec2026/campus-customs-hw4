import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <section className="page narrow center">
      <p className="eyebrow">Lost on Cross Campus</p>
      <h1 className="display">This page wandered off.</h1>
      <p className="lede">It happens to the best of us, usually around midterms.</p>
      <Link to="/products" className="btn">Return to the catalogue</Link>
    </section>
  );
}
