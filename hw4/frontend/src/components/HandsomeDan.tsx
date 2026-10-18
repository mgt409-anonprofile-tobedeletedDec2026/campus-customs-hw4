/** Hand-drawn Handsome Dan, the bulldog who runs the chat counter. */
export default function HandsomeDan({
  className = "",
  title = "Handsome Dan",
  thinking = false,
}: {
  className?: string;
  title?: string;
  thinking?: boolean;
}) {
  return (
    <svg
      className={`dan-art${thinking ? " is-thinking" : ""} ${className}`}
      viewBox="0 0 120 120"
      role="img"
      aria-label={title}
    >
      <title>{title}</title>
      {/* Sweater */}
      <path d="M14 120 C16 98 36 88 60 88 C84 88 104 98 106 120 Z" fill="#00356b" />
      <path d="M40 91 C46 98 74 98 80 91" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" />
      <text x="60" y="115" textAnchor="middle" fontFamily="Georgia, serif" fontWeight="700" fontSize="18" fill="#fff">Y</text>
      {/* Head (tilts while thinking; the sweater stays put) */}
      <g className="dan-head-group">
      {/* Ears */}
      <path d="M30 36 C18 26 8 38 17 50 C22 45 27 41 34 39 Z" fill="#b98c62" stroke="#1d2433" strokeWidth="2" strokeLinejoin="round" />
      <path d="M90 36 C102 26 112 38 103 50 C98 45 93 41 86 39 Z" fill="#b98c62" stroke="#1d2433" strokeWidth="2" strokeLinejoin="round" />
      {/* Head */}
      <path d="M20 60 C18 35 38 22 60 22 C82 22 102 35 100 60 C99 80 85 94 60 95 C35 94 21 80 20 60 Z" fill="#f6f1e8" stroke="#1d2433" strokeWidth="2.2" />
      {/* Brindle patch */}
      <path d="M30 44 C34 36 50 36 54 46 C56 54 50 60 42 60 C33 60 28 52 30 44 Z" fill="#d7b48d" />
      {/* Brow wrinkles */}
      <path d="M49 34 Q60 29 71 34" fill="none" stroke="#1d2433" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M52 39.5 Q60 36 68 39.5" fill="none" stroke="#1d2433" strokeWidth="1.6" strokeLinecap="round" />
      {/* Eyes */}
      <g className="dan-eye">
        <circle cx="43" cy="51" r="5" fill="#1d2433" />
        <circle cx="44.6" cy="49.4" r="1.6" fill="#fff" />
      </g>
      <g className="dan-eye">
        <circle cx="77" cy="51" r="5" fill="#1d2433" />
        <circle cx="78.6" cy="49.4" r="1.6" fill="#fff" />
      </g>
      {/* Muzzle */}
      <ellipse cx="60" cy="70" rx="24" ry="15" fill="#fffaf2" stroke="#1d2433" strokeWidth="1.4" />
      {/* Nose */}
      <path d="M50 60 C50 54 70 54 70 60 C70 65 63 67 60 67 C57 67 50 65 50 60 Z" fill="#1d2433" />
      <ellipse cx="56" cy="58.5" rx="3" ry="1.4" fill="#4a5466" />
      <path d="M60 67 L60 72" stroke="#1d2433" strokeWidth="1.8" strokeLinecap="round" />
      {/* Jowls */}
      <path d="M41 72 C47 81 56 79 60 72 C64 79 73 81 79 72" fill="none" stroke="#1d2433" strokeWidth="2" strokeLinecap="round" />
      {/* Underbite */}
      <path d="M48 79 C52 88 68 88 72 79 C66 82 54 82 48 79 Z" fill="#e3d3bf" stroke="#1d2433" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M51.5 80.5 L53.5 75.5 L55.5 81" fill="#fff" stroke="#1d2433" strokeWidth="1.2" strokeLinejoin="round" />
      <path d="M64.5 81 L66.5 75.5 L68.5 80.5" fill="#fff" stroke="#1d2433" strokeWidth="1.2" strokeLinejoin="round" />
      </g>
    </svg>
  );
}
