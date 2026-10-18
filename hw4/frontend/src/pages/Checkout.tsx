import { Link } from "react-router-dom";
import HandsomeDan from "../components/HandsomeDan";

export default function Checkout() {
  return (
    <section className="page narrow center construction">
      <div className="construction-tape" aria-hidden="true">
        <span>Under Construction</span>
      </div>
      <HandsomeDan className="construction-dan" title="Handsome Dan in a hard hat, figuratively" />
      <p className="eyebrow">Checkout</p>
      <h1 className="display">Under Construction</h1>
      <p className="lede">
        The register is being hand-built from reclaimed Old Campus oak by a craftsman who refuses
        to be rushed. Your bag will wait for you, exactly as you left it. No card was charged,
        because there is nowhere yet to put one.
      </p>
      <div className="hero-actions construction-actions">
        <Link to="/bag" className="btn">Back to your bag</Link>
        <Link to="/products" className="btn btn-ghost">Keep browsing</Link>
      </div>
    </section>
  );
}
