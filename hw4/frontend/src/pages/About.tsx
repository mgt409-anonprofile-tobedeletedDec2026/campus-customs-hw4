import { Link } from "react-router-dom";
import HandsomeDan from "../components/HandsomeDan";

export default function About() {
  return (
    <article className="page narrow about">
      <p className="eyebrow">Our Story</p>
      <h1 className="display">A small shop with a very particular shade of blue.</h1>

      <p className="lede dropcap">
        New Haven, a Tuesday. Rain on the slate roofs. Somewhere a carillon is practicing
        something it hasn&rsquo;t quite mastered. Inside a shop on Broadway, a sweatshirt is being
        folded with the seriousness most people reserve for flags. That is us. That has always
        been us.
      </p>

      <section className="about-section">
        <h2>The Shop</h2>
        <p>
          Campus Customs outfits the people who make up a university: the first-years who just
          arrived, the seniors pretending they aren&rsquo;t sentimental, the alumni who come back
          every fall, and the parents who finally get to say it out loud. Crewnecks for the long
          walk to a nine o&rsquo;clock seminar. Quarter-zips for the professional schools. Hoodies
          for the bleachers. A dad shirt, because somebody earned it.
        </p>
      </section>

      <section className="about-section">
        <h2>The Blue</h2>
        <p>
          You cannot buy Yale blue at a paint store. We&rsquo;ve tried. It is darker than navy at
          dusk and brighter than navy at noon, and it looks best on a gray morning with a coffee
          in hand. Every residential college crest, varsity wordmark, and professional school
          shield in our catalogue is chosen to sit well against it.
        </p>
      </section>

      <section className="about-section about-dan">
        <HandsomeDan className="about-dan-art" />
        <div>
          <h2>The Dog</h2>
          <p>
            Every great institution needs a face. Ours has jowls. Handsome Dan minds the counter
            online, answers questions about sizes and stock, and will tell you plainly when
            something is sold out. Honesty, it turns out, is a very bulldog quality.
          </p>
        </div>
      </section>

      <section className="about-section">
        <h2>Come By</h2>
        <p>The catalogue is open day and night. Pull on something blue, and stay a while.</p>
        <Link to="/products" className="btn">Browse the catalogue</Link>
      </section>
    </article>
  );
}
