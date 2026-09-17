export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—"
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000)
  if (Number.isNaN(s)) return "—"
  if (s < 60) return "just now"
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  if (s < 86400 * 30) return `${Math.floor(s / 86400)}d ago`
  return new Date(iso).toLocaleDateString()
}

export function fmtTokens(v: number): string {
  if (v >= 1_000_000) return `${Math.round((v / 1_000_000) * 10) / 10}M`
  if (v >= 1_000) return `${Math.round((v / 1_000) * 10) / 10}K`
  return v.toLocaleString()
}

export function fmtCost(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `$${v.toFixed(4)}`
}

export function fmtMs(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `${Math.round(v)}ms`
}
