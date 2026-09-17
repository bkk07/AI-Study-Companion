import { useEffect, useMemo, useState } from "react"
import { AnimatePresence, motion, useReducedMotion } from "framer-motion"
import { Check, ChevronDown, Minus, Search } from "lucide-react"
import { cn } from "@/lib/utils"

export type TreeConcept = { id: string; title: string }
export type TreeSubtopic = { id: string; title: string; concepts: TreeConcept[] }
export type TreeTopic = { id: string; title: string; subtopics: TreeSubtopic[] }

/** Minimal backend cover: fully-checked topics collapse to topic_ids, etc. */
export type TreeCover = { topicIds: string[]; subtopicIds: string[]; conceptIds: string[] }

export type SelectionCounts = {
  topics: number
  subtopics: number
  concepts: number
}

export function conceptIdsOfTopic(topic: TreeTopic): string[] {
  return topic.subtopics.flatMap((s) => s.concepts.map((c) => c.id))
}

/** All checked concept ids. */
export function checkedConceptIds(topics: TreeTopic[], checked: Set<string>): string[] {
  const out: string[] = []
  for (const t of topics) {
    for (const s of t.subtopics) {
      for (const c of s.concepts) {
        if (checked.has(c.id)) out.push(c.id)
      }
    }
  }
  return out
}

/** Collapse a checked set to the minimal topic/subtopic/concept cover. */
export function minimalCover(topics: TreeTopic[], checked: Set<string>): TreeCover {
  const topicIds: string[] = []
  const subtopicIds: string[] = []
  const conceptIds: string[] = []
  const coveredTopic = new Set<string>()
  for (const t of topics) {
    const ids = conceptIdsOfTopic(t)
    if (ids.length > 0 && ids.every((id) => checked.has(id))) {
      topicIds.push(t.id)
      coveredTopic.add(t.id)
    }
  }
  for (const t of topics) {
    for (const s of t.subtopics) {
      const ids = s.concepts.map((c) => c.id)
      if (ids.length === 0 || !ids.every((id) => checked.has(id))) {
        for (const id of ids) if (checked.has(id)) conceptIds.push(id)
      } else if (!coveredTopic.has(t.id)) {
        subtopicIds.push(s.id)
      }
    }
  }
  return { topicIds, subtopicIds, conceptIds }
}

/** Summary: fully-selected topics, fully-selected subtopics, total concepts.
 *
 * Subtopics are counted even when their parent topic is fully selected —
 * the summary describes coverage ("your selection spans N subtopics"), not
 * the minimal backend cover (see minimalCover). Counting this way, selecting
 * "Entire Project" shows every topic, subtopic, and concept as selected.
 */
export function selectionCounts(topics: TreeTopic[], checked: Set<string>): SelectionCounts {
  let topicCount = 0
  let subCount = 0
  let conceptCount = 0
  for (const t of topics) {
    const ids = conceptIdsOfTopic(t)
    if (ids.length > 0 && ids.every((id) => checked.has(id))) topicCount += 1
    for (const s of t.subtopics) {
      const sIds = s.concepts.map((c) => c.id)
      if (sIds.length > 0 && sIds.every((id) => checked.has(id))) subCount += 1
      for (const id of sIds) if (checked.has(id)) conceptCount += 1
    }
  }
  return { topics: topicCount, subtopics: subCount, concepts: conceptCount }
}

type CheckState = "checked" | "indeterminate" | "unchecked"

function AnimatedCheck({ state, depth = 0 }: { state: CheckState; depth?: number }) {
  const reduce = useReducedMotion()
  return (
    <span
      className={cn(
        "flex h-5 w-5 shrink-0 items-center justify-center rounded-md border transition-colors duration-150",
        state !== "unchecked"
          ? "border-indigo-600 bg-indigo-600 text-white"
          : "border-slate-300 bg-white text-transparent",
      )}
    >
      <motion.span
        key={state}
        initial={reduce ? false : { scale: 0.3, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 550, damping: 24, delay: reduce ? 0 : Math.min(depth * 0.03, 0.18) }}
        className="flex"
      >
        {state === "indeterminate" ? <Minus size={13} strokeWidth={3.5} /> : <Check size={13} strokeWidth={3} />}
      </motion.span>
    </span>
  )
}

/** Number that slides subtly whenever the value changes. */
export function AnimatedNumber({ value, className }: { value: number; className?: string }) {
  const reduce = useReducedMotion()
  return (
    <span className={cn("inline-flex min-w-6 justify-center", className)}>
      <motion.span
        key={value}
        initial={reduce ? false : { y: 6, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.16 }}
        className="inline-block"
      >
        {value}
      </motion.span>
    </span>
  )
}

function Highlight({ text, needle }: { text: string; needle: string }) {
  const q = needle.trim()
  if (!q) return <>{text}</>
  const idx = text.toLowerCase().indexOf(q.toLowerCase())
  if (idx === -1) return <>{text}</>
  return (
    <>
      {text.slice(0, idx)}
      <mark className="rounded-sm bg-amber-200 px-0.5 text-inherit">{text.slice(idx, idx + q.length)}</mark>
      {text.slice(idx + q.length)}
    </>
  )
}

function ExpandIcon({ open }: { open: boolean }) {
  return (
    <motion.span
      animate={{ rotate: open ? 0 : -90 }}
      transition={{ duration: 0.16 }}
      className="flex rounded p-0.5 text-slate-400"
    >
      <ChevronDown size={15} />
    </motion.span>
  )
}

export function SelectionSummary({ counts }: { counts: SelectionCounts }) {
  return (
    <p className="text-sm text-slate-600">
      Selected knowledge ·{" "}
      <strong className="font-semibold text-slate-900">
        <AnimatedNumber value={counts.topics} /> Topic{counts.topics === 1 ? "" : "s"}
      </strong>
      {" · "}
      <strong className="font-semibold text-slate-900">
        <AnimatedNumber value={counts.subtopics} /> Subtopic{counts.subtopics === 1 ? "" : "s"}
      </strong>
      {" · "}
      <strong className="font-semibold text-slate-900">
        <AnimatedNumber value={counts.concepts} /> Concept{counts.concepts === 1 ? "" : "s"}
      </strong>
    </p>
  )
}

export function KnowledgeTreeSelector({
  topics,
  checked,
  onChange,
  searchPlaceholder = "Search topics, subtopics, concepts...",
  expandConceptId = null,
}: {
  topics: TreeTopic[]
  checked: Set<string>
  onChange: (next: Set<string>) => void
  searchPlaceholder?: string
  expandConceptId?: string | null
}) {
  const [search, setSearch] = useState("")
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(topics.map((t) => t.id)))
  const reduce = useReducedMotion()

  // Deep link: reveal the ancestors of a focused concept.
  useEffect(() => {
    if (!expandConceptId) return
    for (const t of topics) {
      for (const s of t.subtopics) {
        if (s.concepts.some((c) => c.id === expandConceptId)) {
          setExpanded((prev) => new Set(prev).add(t.id).add(s.id))
          return
        }
      }
    }
  }, [topics, expandConceptId])

  const toggle = (ids: string[], select: boolean) => {
    const next = new Set(checked)
    for (const id of ids) {
      if (select) next.add(id)
      else next.delete(id)
    }
    onChange(next)
  }

  const toggleIds = (ids: string[]) => {
    const all = ids.length > 0 && ids.every((id) => checked.has(id))
    toggle(ids, !all)
  }

  const setExpandedId = (id: string, open: boolean) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (open) next.add(id)
      else next.delete(id)
      return next
    })
  }

  const stateOf = (ids: string[]): CheckState => {
    if (ids.length === 0) return "unchecked"
    const n = ids.filter((id) => checked.has(id)).length
    if (n === ids.length) return "checked"
    if (n > 0) return "indeterminate"
    return "unchecked"
  }

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()
    if (!needle) return topics
    return topics
      .map((t) => {
        if (t.title.toLowerCase().includes(needle)) return { ...t, _forceOpen: true as const }
        const subs = t.subtopics
          .map((s) => {
            if (s.title.toLowerCase().includes(needle)) return { ...s, _forceOpen: true as const }
            const concepts = s.concepts.filter((c) => c.title.toLowerCase().includes(needle))
            if (concepts.length > 0) return { ...s, concepts }
            return null
          })
          .filter((s): s is NonNullable<typeof s> => s !== null)
        if (subs.length > 0) return { ...t, subtopics: subs, _forceOpen: true as const }
        return null
      })
      .filter((t): t is NonNullable<typeof t> => t !== null)
  }, [topics, search])

  const searching = search.trim().length > 0
  const totalConcepts = topics.reduce((n, t) => n + conceptIdsOfTopic(t).length, 0)
  const checkedCount = checked.size

  const rowClass = (state: CheckState, strong = false) =>
    cn(
      "flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left transition-colors duration-150",
      "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-1",
      state === "checked"
        ? strong
          ? "bg-indigo-100/70 hover:bg-indigo-100"
          : "bg-indigo-50/70 hover:bg-indigo-50"
        : "hover:bg-slate-100/80",
    )

  const needle = search.trim()

  return (
    <div>
      <div className="relative mb-2">
        <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={searchPlaceholder}
          aria-label="Search knowledge tree"
          className="w-full rounded-xl border border-slate-200 py-2.5 pl-9 pr-3 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        />
      </div>

      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs text-slate-500" aria-live="polite">
          <AnimatedNumber value={checkedCount} className="font-semibold text-slate-700" /> concept{checkedCount === 1 ? "" : "s"} selected
        </span>
        <span className="flex gap-3">
          <button
            type="button"
            onClick={() => onChange(new Set(topics.flatMap((t) => conceptIdsOfTopic(t))))}
            className="text-xs font-medium text-indigo-600 hover:underline"
          >
            Select all
          </button>
          <button
            type="button"
            onClick={() => onChange(new Set())}
            className="text-xs font-medium text-slate-400 transition-colors hover:text-red-600 hover:underline"
          >
            Clear all
          </button>
        </span>
      </div>

      <div role="tree" aria-label="Knowledge tree" className="max-h-96 space-y-1 overflow-y-auto rounded-2xl border border-slate-200 bg-white p-2 shadow-sm">
        {/* Entire project root */}
        <ProjectRow
          title="Entire Project"
          subtitle={`${topics.length} topics · ${totalConcepts} concepts`}
          state={stateOf(topics.flatMap((t) => conceptIdsOfTopic(t)))}
          onToggle={() => toggleIds(topics.flatMap((t) => conceptIdsOfTopic(t)))}
          rowClass={rowClass}
          needle={needle}
        />

        {visible.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-slate-400">
            No matches for “{search.trim()}” — try a different term.
          </p>
        )}

        {visible.map((t) => {
          const ids = conceptIdsOfTopic(t)
          const tState = stateOf(ids)
          const open = searching || expanded.has(t.id)
          const selectedCount = ids.filter((id) => checked.has(id)).length
          return (
            <div key={t.id} role="treeitem" aria-expanded={open} aria-level={2} aria-checked={tState === "indeterminate" ? "mixed" : tState === "checked"} aria-label={t.title}>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  role="checkbox"
                  aria-checked={tState === "indeterminate" ? "mixed" : tState === "checked"}
                  aria-label={`Select topic ${t.title}`}
                  onClick={() => toggleIds(ids)}
                  className={cn(rowClass(tState, true), "min-w-0 flex-1")}
                >
                  <AnimatedCheck state={tState} depth={0} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-bold text-slate-900">
                      <Highlight text={t.title} needle={needle} />
                    </span>
                    <span className="block text-[11px] text-slate-400">
                      {t.subtopics.length} subtopics
                    </span>
                  </span>
                  <span
                    aria-label={`${selectedCount} of ${ids.length} concepts selected`}
                    className={cn(
                      "font-mono-data shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold",
                      tState === "checked" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-500",
                    )}
                  >
                    {selectedCount}/{ids.length}
                  </span>
                </button>
                <button
                  type="button"
                  aria-label={open ? `Collapse ${t.title}` : `Expand ${t.title}`}
                  aria-expanded={open}
                  onClick={() => setExpandedId(t.id, !open)}
                  className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                >
                  <ExpandIcon open={open} />
                </button>
              </div>

              <AnimatePresence initial={false}>
                {open && (
                  <motion.div
                    key={`sub-${t.id}`}
                    initial={reduce ? false : { height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={reduce ? undefined : { height: 0, opacity: 0 }}
                    transition={{ duration: 0.22, ease: "easeInOut" }}
                    className="overflow-hidden"
                  >
                    <div role="group" aria-label={`${t.title} subtopics`} className="ml-5 space-y-0.5 border-l-2 border-slate-100 py-1 pl-2">
                      {t.subtopics.map((s) => {
                        const sIds = s.concepts.map((c) => c.id)
                        const sState = stateOf(sIds)
                        const sOpen = searching || expanded.has(s.id)
                        return (
                          <div key={s.id} role="treeitem" aria-expanded={sOpen} aria-level={3} aria-checked={sState === "indeterminate" ? "mixed" : sState === "checked"} aria-label={s.title}>
                            <div className="flex items-center gap-1">
                              <button
                                type="button"
                                role="checkbox"
                                aria-checked={sState === "indeterminate" ? "mixed" : sState === "checked"}
                                aria-label={`Select subtopic ${s.title}`}
                                onClick={() => toggleIds(sIds)}
                                className={cn(rowClass(sState), "min-w-0 flex-1")}
                              >
                                <AnimatedCheck state={sState} depth={1} />
                                <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-slate-700">
                                  <Highlight text={s.title} needle={needle} />
                                </span>
                                <span className="font-mono-data shrink-0 text-[11px] text-slate-400">
                                  {sIds.filter((id) => checked.has(id)).length}/{sIds.length}
                                </span>
                              </button>
                              <button
                                type="button"
                                aria-label={sOpen ? `Collapse ${s.title}` : `Expand ${s.title}`}
                                aria-expanded={sOpen}
                                onClick={() => setExpandedId(s.id, !sOpen)}
                                className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
                              >
                                <ExpandIcon open={sOpen} />
                              </button>
                            </div>
                            <AnimatePresence initial={false}>
                              {sOpen && (
                                <motion.div
                                  key={`con-${s.id}`}
                                  initial={reduce ? false : { height: 0, opacity: 0 }}
                                  animate={{ height: "auto", opacity: 1 }}
                                  exit={reduce ? undefined : { height: 0, opacity: 0 }}
                                  transition={{ duration: 0.22, ease: "easeInOut" }}
                                  className="overflow-hidden"
                                >
                                  <div role="group" aria-label={`${s.title} concepts`} className="ml-5 space-y-0.5 border-l-2 border-slate-100 py-1 pl-2">
                                    {s.concepts.map((c) => {
                                      const on = checked.has(c.id)
                                      return (
                                        <div key={c.id} role="treeitem" aria-level={4} aria-checked={on} aria-label={c.title}>
                                          <button
                                            type="button"
                                            role="checkbox"
                                            aria-checked={on}
                                            aria-label={`Select concept ${c.title}`}
                                            onClick={() => toggleIds([c.id])}
                                            className={cn(rowClass(on ? "checked" : "unchecked"), "w-full py-1.5")}
                                          >
                                            <AnimatedCheck state={on ? "checked" : "unchecked"} depth={2} />
                                            <span className="truncate text-[13px] text-slate-600">
                                              <Highlight text={c.title} needle={needle} />
                                            </span>
                                          </button>
                                        </div>
                                      )
                                    })}
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </div>
                        )
                      })}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function ProjectRow({
  title,
  subtitle,
  state,
  onToggle,
  rowClass,
  needle,
}: {
  title: string
  subtitle: string
  state: CheckState
  onToggle: () => void
  rowClass: (s: CheckState, strong?: boolean) => string
  needle: string
}) {
  return (
    <div role="treeitem" aria-level={1} aria-checked={state === "indeterminate" ? "mixed" : state === "checked"} aria-label={title} className="rounded-xl border border-slate-200 bg-slate-50/60">
      <button
        type="button"
        role="checkbox"
        aria-checked={state === "indeterminate" ? "mixed" : state === "checked"}
        aria-label={`Select ${title}`}
        onClick={onToggle}
        className={cn(rowClass(state, true), "px-3 py-2.5")}
      >
        <AnimatedCheck state={state} depth={0} />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-bold text-slate-900">
            <Highlight text={title} needle={needle} />
          </span>
          <span className="block text-[11px] text-slate-400">{subtitle}</span>
        </span>
      </button>
    </div>
  )
}
