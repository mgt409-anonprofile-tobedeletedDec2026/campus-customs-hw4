import { Link } from "react-router-dom";
import Skyline from "./Skyline";

export default function Footer() {
  return (
    <footer className="site-footer">
      <Skyline className="footer-skyline" variant="light" />
      <div className="footer-inner">
        <div>
          <p className="footer-mark">Campus Customs</p>
          <p className="footer-note">
            Yale blue, worn well. A shop in New Haven, Connecticut.
          </p>
        </div>
        <nav className="footer-links" aria-label="Footer">
          <Link to="/products">The Catalogue</Link>
          <Link to="/about">Our Story</Link>
          <Link to="/login">Log in</Link>
          <Link to="/create-account">Create account</Link>
        </nav>
      </div>
      <p className="footer-fine">
        A course homework project. Not affiliated with, and not a storefront for, any real retailer.
      </p>
    </footer>
  );
}
