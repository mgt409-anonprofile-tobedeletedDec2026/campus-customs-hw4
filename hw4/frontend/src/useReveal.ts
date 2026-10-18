import { RefObject, useEffect, useState } from "react";

const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/**
 * Fade an element gently into view the first time it scrolls on screen.
 * Returns the class to apply. Shoppers who prefer reduced motion just see the element.
 */
export function useReveal(ref: RefObject<HTMLElement>): string {
  const [state, setState] = useState<"off" | "hidden" | "shown">(() => (prefersReducedMotion() ? "off" : "hidden"));

  useEffect(() => {
    if (state !== "hidden" || !ref.current) return;
    const el = ref.current;
    if (!("IntersectionObserver" in window)) {
      setState("shown");
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setState("shown");
          observer.disconnect();
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [state, ref]);

  return state === "off" ? "" : state === "hidden" ? "reveal" : "reveal is-visible";
}
