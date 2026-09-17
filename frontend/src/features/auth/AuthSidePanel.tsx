import { useEffect, useState } from "react"
import { BookOpen, Compass, Sparkles, Target } from "lucide-react"

export type AuthSlide = {
  title: string
  text: string
}

type Props = {
  image: string
  imageAlt: string
  title: string
  subtitle: string
  slides: AuthSlide[]
}

const SLIDE_ICONS = [
  <Sparkles key="s" size={18} />,
  <Target key="t" size={18} />,
  <Compass key="c" size={18} />,
]

const ROTATE_MS = 4500

/**
 * Shared showcase panel for login/register: full-bleed Unsplash photo with an
 * indigo-950 gradient overlay so white text stays legible and the brand
 * palette (indigo-600 primary, slate surfaces) carries through. The solid
 * bg-indigo-950 underneath doubles as the offline/no-image fallback. The
 * bottom glass card auto-rotates factual product spotlights (no metrics,
 * nothing to go stale).
 */
export function AuthSidePanel({ image, imageAlt, title, subtitle, slides }: Props) {
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const count = slides.length

  useEffect(() => {
    if (paused || count < 2) return
    const id = window.setInterval(() => setIndex((i) => (i + 1) % count), ROTATE_MS)
    return () => window.clearInterval(id)
  }, [paused, count])

  const slide = slides[Math.min(index, count - 1)]

  return (
    <div className="relative hidden w-1/2 flex-col overflow-hidden bg-indigo-950 text-white lg:flex">
      <img
        src={image}
        alt={imageAlt}
        className="absolute inset-0 h-full w-full object-cover"
        loading="eager"
      />
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-950/95 via-indigo-950/70 to-slate-900/60" />
      <div className="absolute inset-x-0 bottom-0 h-56 bg-gradient-to-t from-slate-950/80 to-transparent" />
      <div className="relative z-10 flex h-full flex-col p-12">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500 shadow-lg shadow-indigo-950/40 ring-1 ring-white/20">
            <BookOpen size={18} />
          </div>
          <span className="text-lg font-semibold tracking-tight">Study Companion</span>
        </div>
        <div className="flex flex-1 flex-col justify-end pb-2">
          <h1 className="font-display max-w-md text-4xl font-semibold leading-tight tracking-tight">
            {title}
          </h1>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-indigo-200">{subtitle}</p>

          {slide && (
            <div
              className="mt-6 max-w-md rounded-2xl bg-white/10 p-5 ring-1 ring-white/20 backdrop-blur-md"
              onMouseEnter={() => setPaused(true)}
              onMouseLeave={() => setPaused(false)}
            >
              <div className="flex items-start gap-3">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-400/20 text-indigo-200 ring-1 ring-white/20">
                  {SLIDE_ICONS[index % SLIDE_ICONS.length]}
                </div>
                <div key={index} className="min-w-0">
                  <div className="text-sm font-semibold text-white">{slide.title}</div>
                  <p className="mt-1 text-sm leading-relaxed text-indigo-100/90">{slide.text}</p>
                </div>
              </div>
              {count > 1 && (
                <div className="mt-4 flex gap-1.5">
                  {slides.map((s, i) => (
                    <button
                      key={s.title}
                      type="button"
                      aria-label={`Show ${s.title}`}
                      onClick={() => setIndex(i)}
                      className={`h-1 rounded-full transition-all ${
                        i === index ? "w-6 bg-white" : "w-2 bg-white/30 hover:bg-white/50"
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
