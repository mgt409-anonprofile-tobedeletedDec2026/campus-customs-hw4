import skylineInk from "../assets/yale-skyline.webp";
import skylineLight from "../assets/yale-skyline-light.webp";

/**
 * Engraved Yale skyline (Harkness Tower, Sterling Memorial Library, Collegiate Gothic rooftops, elms).
 * Artwork generated with ChatGPT from our prompt (see AI_prompts.md), with the white paper removed so
 * the ink sits on any background. "ink" is Yale blue for light pages; "light" is pale for the blue footer.
 */
export default function Skyline({ className = "", variant = "ink" }: { className?: string; variant?: "ink" | "light" }) {
  return (
    <img
      className={className}
      src={variant === "light" ? skylineLight : skylineInk}
      alt=""
      aria-hidden="true"
      width={1800}
      height={600}
      decoding="async"
    />
  );
}
