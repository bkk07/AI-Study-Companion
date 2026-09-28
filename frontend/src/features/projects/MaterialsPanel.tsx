import { useCallback, useEffect, useRef, useState } from "react"
import { CheckCircle2, Clock3, Eye, FileText, Loader2, RotateCw, Trash2, UploadCloud } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { EmptyState, ErrorBox, LoadingState, SectionHeader } from "@/components/ui"
import { cn } from "@/lib/utils"

type Enrichment = {
  extraction: string
  embeddings: string | null
  structure: string | null
}

type Material = {
  id: string
  project_id: string
  filename: string
  status: string
  page_count: number | null
  error_message: string | null
  created_at: string
  enrichment: Enrichment | null
}

function isActiveStage(s: string | null | undefined) {
  return s === "pending" || s === "running"
}

/** True while embeddings / knowledge-map jobs are still queued/running. */
function enrichmentActive(m: Material) {
  const e = m.enrichment
  return !!e && (isActiveStage(e.embeddings) || isActiveStage(e.structure))
}

/** Human-readable tail of what is still being built after extraction. */
function stageText(m: Material): string | null {
  const e = m.enrichment
  if (!e || e.extraction !== "ready" || !enrichmentActive(m)) return null
  const bits: string[] = []
  if (isActiveStage(e.embeddings)) bits.push("search index")
  if (isActiveStage(e.structure)) bits.push("learning map")
  return bits.length ? `Finishing: ${bits.join(" + ")}…` : null
}

function StatusPill({ material }: { material: Material }) {
  const { status } = material
  // Honest states: backend reports `processing` while search index /
  // learning map jobs are still pending/running (materials.py). Never show
  // green Ready until enrichment is actually done — tutor/quizzes need the
  // embeddings, so premature Ready is why "Ready" answered "no information".
  if (status === "ready" && !enrichmentActive(material)) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
        <CheckCircle2 size={12} /> Ready
      </span>
    )
  }
  if (status === "failed")
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
        Failed
      </span>
    )
  if (status === "processing" || (status === "ready" && enrichmentActive(material))) {
    const tail = stageText(material)
    const tip = material.enrichment
      ? `Text extracted — search index: ${material.enrichment.embeddings ?? "done"}, learning map: ${material.enrichment.structure ?? "done"}`
      : undefined
    return (
      <span title={tip} className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600">
        <Loader2 size={12} className="animate-spin" /> {tail ?? "Processing"}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
      <Clock3 size={12} /> Queued
    </span>
  )
}

export function MaterialsPanel({ projectId }: { projectId: string }) {
  const [materials, setMaterials] = useState<Material[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [view, setView] = useState<"library" | "upload">("library")
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async (opts?: { poll?: boolean }) => {
    try {
      // Initial open is cache-first (no DB hit on tab switches). Only the
      // 2s live poll while jobs run bypasses the cache so pending → ready
      // transitions still show up immediately.
      const res = await apiClient.get<Material[]>(`/projects/${projectId}/materials`, {
        ...(opts?.poll ? { noCache: true } : {}),
      })
      setMaterials(res.data)
      setError(null)
    } catch (e: unknown) {
      const { status, message: detail } = apiError(e)
      if (status === 404) setError("Project not found for this view.")
      else setError(detail ?? "Failed to load materials.")
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    setLoading(true)
    void load()
  }, [load])

  useEffect(() => {
    if (!materials?.some((m) => m.status === "pending" || m.status === "processing" || enrichmentActive(m))) return
    // 2s while anything is live: extraction now finishes in ~1s, so a 5s
    // cadence would skip the Processing state entirely between polls.
    const t = setInterval(() => void load({ poll: true }), 2000)
    return () => clearInterval(t)
  }, [materials, load])

  const upload = useCallback(
    async (file: File) => {
      setUploading(true)
      setUploadError(null)
      try {
        const form = new FormData()
        form.append("file", file, file.name)
        await apiClient.post(`/projects/${projectId}/materials`, form, {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 120000,
        })
        await load({ poll: true })
        setView("library")
      } catch (e: unknown) {
        const { status, message: detail } = apiError(e)
        if (status === 413) setUploadError("That file is over the 10MB limit.")
        else setUploadError(detail ?? "Upload failed — only PDF files are accepted.")
      } finally {
        setUploading(false)
      }
    },
    [projectId, load],
  )

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file && !uploading) void upload(file)
  }

  return (
    <div>
      <SectionHeader
        title="Documents"
        subtitle="PDF library grounded for tutor, quizzes, and maps"
        action={
          <div className="flex rounded-lg bg-slate-100 p-1">
            {(["library", "upload"] as const).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-sm font-medium capitalize transition-colors",
                  view === v ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700",
                )}
              >
                {v}
              </button>
            ))}
          </div>
        }
      />

      {view === "upload" && (
        <div>
          <div
            role="button"
            tabIndex={0}
            aria-label="Upload a PDF"
            onClick={() => fileRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter") fileRef.current?.click()
            }}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={cn(
              "flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-6 py-20 text-center transition-all",
              dragOver ? "border-indigo-500 bg-indigo-50" : "border-slate-200 bg-white hover:border-slate-300",
            )}
          >
            <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-50 text-indigo-600">
              <UploadCloud size={22} />
            </span>
            <p className="mt-3 text-sm font-semibold text-slate-800">{uploading ? "Uploading…" : "Drop a PDF here, or click to browse"}</p>
            <p className="mt-1 text-xs text-slate-500">PDF only · max 10MB · we&apos;ll extract it and build your learning map</p>
            {uploading && <Loader2 className="mt-3 h-5 w-5 animate-spin text-indigo-600" />}
            <input
              ref={fileRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                e.target.value = ""
                if (file) void upload(file)
              }}
            />
          </div>
          {uploadError && (
            <div className="mt-4">
              <ErrorBox message={uploadError} />
            </div>
          )}
        </div>
      )}

      {view === "library" && (
        <div>
          {loading ? (
            <LoadingState text="Loading materials…" />
          ) : error ? (
            <ErrorBox message={error} onRetry={() => void load({ poll: true })} />
          ) : !materials || materials.length === 0 ? (
            <div className="rounded-xl border border-slate-200 bg-white">
              <EmptyState
                icon={<FileText size={24} />}
                title="No documents yet"
                hint="Upload your first PDF — structure, tutor answers, and quizzes all grow from it."
              />
            </div>
          ) : (
            <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Document</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Pages</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">Uploaded</th>
                    <th className="px-6 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {materials.map((m, i) => (
                    <tr key={m.id} className={`border-b border-slate-50 transition-colors hover:bg-slate-50 ${i === materials.length - 1 ? "border-0" : ""}`}>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-50 text-red-400">
                            <FileText size={15} />
                          </span>
                          <div className="min-w-0">
                            <div className="truncate font-medium text-slate-800">{m.filename}</div>
                            {m.status === "failed" && m.error_message && (
                              <div className="truncate text-xs text-red-500">{m.error_message}</div>
                            )}
                            {m.status !== "failed" && stageText(m) && (
                              <div className="truncate text-xs text-slate-400">{stageText(m)}</div>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="font-mono-data px-4 py-4 text-slate-600">{m.page_count ?? "—"}</td>
                      <td className="px-4 py-4"><StatusPill material={m} /></td>
                      <td className="px-4 py-4 text-xs text-slate-500">{new Date(m.created_at).toLocaleDateString()}</td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-1">
                          <button type="button" className="rounded p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600" title="View">
                            <Eye size={15} />
                          </button>
                          <button type="button" onClick={() => void load({ poll: true })} className="rounded p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600" title="Refresh">
                            <RotateCw size={15} />
                          </button>
                          <button type="button" className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Delete (coming soon)">
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {uploadError && (
            <div className="mt-4">
              <ErrorBox message={uploadError} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
