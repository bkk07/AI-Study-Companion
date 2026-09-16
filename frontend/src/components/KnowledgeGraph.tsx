export function KnowledgeGraphSVG() {
  return (
    <svg viewBox="0 0 400 400" className="w-full max-w-sm opacity-80" fill="none" aria-hidden>
      <line x1="200" y1="200" x2="120" y2="120" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="300" y2="130" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="100" y2="280" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="310" y2="290" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="200" y2="320" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="60" y2="190" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="200" y1="200" x2="340" y2="200" stroke="#a5b4fc" strokeWidth="1.5" />
      <line x1="120" y1="120" x2="60" y2="80" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="120" y1="120" x2="190" y2="60" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="300" y1="130" x2="360" y2="80" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="300" y1="130" x2="350" y2="160" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="100" y1="280" x2="50" y2="320" stroke="#c7d2fe" strokeWidth="1" />
      <line x1="310" y1="290" x2="360" y2="340" stroke="#c7d2fe" strokeWidth="1" />
      {[
        [60, 80], [190, 60], [360, 80], [350, 160], [50, 320],
        [360, 340], [200, 360], [35, 190], [365, 200],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="5" fill="#e0e7ff" stroke="#818cf8" strokeWidth="1" />
      ))}
      {[
        [120, 120], [300, 130], [100, 280], [310, 290], [60, 190], [340, 200], [200, 320],
      ].map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="9" fill="#c7d2fe" stroke="#6366f1" strokeWidth="1.5" />
      ))}
      <circle cx="200" cy="200" r="18" fill="#4f46e5" stroke="#3730a3" strokeWidth="2" />
      <circle cx="200" cy="200" r="10" fill="white" opacity="0.3" />
    </svg>
  )
}
