import React, { useState } from 'react'
import { GenerateForm } from './components/GenerateForm'
import { AudioPlayer } from './components/AudioPlayer'
import { TaskQueue } from './components/TaskQueue'
import { GPUDashboard } from './components/GPUDashboard'
import { TrackHistory } from './components/TrackHistory'
import { useMusicStore } from './stores/musicStore'

function Header() {
  return (
    <header className="border-b border-bg-border bg-bg-secondary/80 backdrop-blur-sm sticky top-0 z-10">
      <div className="max-w-screen-2xl mx-auto px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-blue to-accent-purple flex items-center justify-center text-white text-sm font-bold">
            M
          </div>
          <div>
            <span className="font-semibold text-slate-200 text-sm">MusicForge</span>
            <span className="text-xs text-slate-500 font-mono ml-2">ACE-Step v1.5</span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs font-mono text-slate-500">
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="hover:text-accent-blue transition-colors"
          >
            API Docs
          </a>
          <a
            href="http://localhost:5555"
            target="_blank"
            rel="noreferrer"
            className="hover:text-accent-blue transition-colors"
          >
            Flower
          </a>
          <a
            href="http://localhost:8001/docs"
            target="_blank"
            rel="noreferrer"
            className="hover:text-accent-blue transition-colors"
          >
            ACE-Step
          </a>
        </div>
      </div>
    </header>
  )
}

type View = 'studio' | 'history'

export default function App() {
  const currentTrack = useMusicStore((s) => s.currentTrack)
  const [view, setView] = useState<View>('studio')

  return (
    <div className="min-h-screen bg-bg-primary text-slate-200 flex flex-col">
      <Header />

      {/* Nav tabs */}
      <div className="border-b border-bg-border bg-bg-secondary/40">
        <div className="max-w-screen-2xl mx-auto px-6 flex gap-1">
          {(['studio', 'history'] as View[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`py-2.5 px-4 text-xs font-mono uppercase tracking-wider border-b-2 transition-all ${
                view === v
                  ? 'border-accent-blue text-accent-blue'
                  : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              {v === 'studio' ? 'Studio' : 'History'}
            </button>
          ))}
        </div>
      </div>

      <main className="flex-1 max-w-screen-2xl mx-auto w-full px-6 py-6">
        {view === 'studio' ? (
          <div className="flex flex-col gap-6">
            {/* Main studio area: Generate + Player left, Queue right */}
            <div className="grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-6">
              {/* Left column */}
              <div className="space-y-5">
                <section className="bg-bg-secondary border border-bg-border rounded-xl p-5">
                  <h2 className="text-xs font-mono text-slate-400 uppercase tracking-wider mb-4">
                    Generate
                  </h2>
                  <GenerateForm />
                </section>

                <section>
                  <h2 className="text-xs font-mono text-slate-400 uppercase tracking-wider mb-3">
                    Player
                  </h2>
                  <AudioPlayer track={currentTrack} />
                </section>
              </div>

              {/* Right column — Task Queue */}
              <aside className="bg-bg-secondary border border-bg-border rounded-xl p-5 xl:min-h-[600px]">
                <TaskQueue />
              </aside>
            </div>

            {/* GPU Dashboard */}
            <section className="bg-bg-secondary border border-bg-border rounded-xl p-5">
              <GPUDashboard />
            </section>
          </div>
        ) : (
          <TrackHistory />
        )}
      </main>

      <footer className="border-t border-bg-border py-3 text-center text-xs font-mono text-slate-600">
        MusicForge — ACE-Step v1.5 &middot; GPU Farm Ready
      </footer>
    </div>
  )
}
