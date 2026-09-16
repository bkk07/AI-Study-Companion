import { useCallback, useEffect, useRef, useState } from "react"
import { CheckCircle2, Clock3, FileUp, Loader2, UploadCloud, XCircle } from "lucide-react"
import apiClient from "@/lib/axios"
import { apiError } from "@/lib/api-error"
import { Badge, Card, EmptyState, ErrorBox, LoadingState } from "@/components/ui"
import { cn } from "@/lib/utils"

type Material = {
  id: string
  project_id: string
  filename: string
  status: string
  page_count: number | null
  error_message: string | null
  created_at: string
}

function StatusBadge({ status }: { status: string }) {
  if (status === "ready")
    return (
      <Badge tint="emerald">
        <CheckCircle2 className="h-3 w-3" /> Ready
      </Badge>
    )
  if (status === "failed")
    return (
      <Badge tint="rose">
        <XCircle className="h-3 w-3" /> Failed
      </Badge>
    )
  if (status === "processing")
    return (
      <Badge tint="sky">
        <Loader2 className="h-3 w-3 animate-spin" /> Processing
      </Badge>
    )
  return (
    <Badge tint="amber">
      <Clock3 className="h-3 w-3" /> Queued
    </Badge>
  )
}

export function MaterialsPanel({ projectId }: { projectId: string }) {
  const [materials, setMaterials] = useState<Material[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    try {
      const res = await apiClient.get<Material[]>(`/projects/${projectId}/materials`)
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

  // Auto-refresh while anything is still being processed.
  useEffect(() => {
    if (!materials?.some((m) => m.status === "pending" || m.status === "processing")) return
    const t = setInterval(() => void load(), 5000)
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
        await load()
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
    <div className="space-y-4">
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
          "flex cursor-pointer flex-col items-center rounded-2xl border-2 border-dashed px-6 py-9 text-center transition-all",
          dragOver
            ? "border-violet-500 bg-violet-100/60 shadow-glow"
            : "border-violet-200 bg-violet-50/50 hover:border-violet-400 hover:bg-violet-50",
        )}
      >
        <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-fuchsia-500 text-white shadow-soft">
          <UploadCloud className="h-6 w-6" />
        </span>
        <p className="mt-3 font-bold">{uploading ? "Uploading…" : "Drop a PDF here, or click to browse"}</p>
        <p className="mt-1 text-sm text-muted-foreground">
          PDF only · max 10MB · we&apos;ll extract it and build your learning map
        </p>
        {uploading && <Loader2 className="mt-3 h-5 w-5 animate-spin text-violet-600" />}
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
      {uploadError && <ErrorBox message={uploadError} />}

      {loading ? (
        <LoadingState text="Loading materials…" />
      ) : error ? (
        <ErrorBox message={error} onRetry={() => void load()} />
      ) : !materials || materials.length === 0 ? (
        <EmptyState
          icon={<FileUp className="h-6 w-6" />}
          title="No materials yet"
          hint="Upload your first PDF above — structure, tutor answers, and quizzes all grow from it."
        />
      ) : (
        <div className="grid gap-2.5">
          {materials.map((m) => (
            <Card key={m.id} className="flex items-center gap-3 p-3.5">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-rose-100 text-xs font-extrabold text-rose-600">
                PDF
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-bold">{m.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {m.page_count != null ? `${m.page_count} pages · ` : ""}
                  {new Date(m.created_at).toLocaleDateString()}
                  {m.status === "failed" && m.error_message ? ` · ${m.error_message}` : ""}
                </p>
              </div>
              <StatusBadge status={m.status} />
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
