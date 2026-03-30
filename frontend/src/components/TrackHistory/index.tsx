import React from 'react'
import { useMusicStore } from '../../stores/musicStore'
import type { TaskResult } from '../../api/client'

interface TrackCardProps {
  track: TaskResult
  isActive: boolean
  onSelect: (track: TaskResult) => void
}

function TrackCard({ track, isActive, onSelect }: TrackCardProps) {
  const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  return (
    <div
      onClick={() => onSelect(track)}
      className={`bg-bg-card border rounded-xl p-4 cursor-pointer transition-all hover:border-accent-blue/40 ${
        isActive ? 'border-accent-blue/70' : 'border-bg-border'
      }`}
    >
      {/* Waveform preview (static) */}
      <div className="h-12 bg-bg-tertiary rounded-lg mb-3 flex items-center justify-center overflow-hidden relative">
        <svg viewBox="0 0 120 40" className="w-full h-full opacity-60" preserveAspectRatio="none">
          {Array.from({ length: 40 }).map((_, i) => {
            const h = 5 + Math.abs(Math.sin(i * 0.7 + (track.task_id.charCodeAt(i % 8) || 0))) * 25
            return (
              <rect
                key={i}
                x={i * 3}
                y={(40 - h) / 2}
                width={2}
                height={h}
                fill={isActive ? '#3b82f6' : '#8b5cf6'}
                opacity={0.7}
              />
            )
          })}
        </svg>
        {isActive && (
          <div className="absolute inset-0 flex items-center justify-center bg-bg-card/50 rounded-lg">
            <span className="text-accent-blue text-lg">▶</span>
          </div>
        )}
      </div>

      {/* Info */}
      <p className="text-xs text-slate-300 truncate mb-1">
        {track.metadata?.prompt || 'Generated Track'}
      </p>
      <div className="flex items-center justify-between text-xs font-mono text-slate-500">
        <span>{track.duration ? `${track.duration}s` : ''}</span>
        {track.metadata?.lora && (
          <span className="text-accent-purple truncate max-w-[80px]">{track.metadata.lora}</span>
        )}
      </div>
      {track.metadata?.generation_time && (
        <div className="text-xs font-mono text-slate-600 mt-0.5">
          Gen: {track.metadata.generation_time}s
        </div>
      )}

      {/* Download */}
      {track.audio_url && (
        <a
          href={`${apiBase}${track.audio_url}`}
          download={`musicforge-${track.task_id.slice(0, 8)}.wav`}
          onClick={(e) => e.stopPropagation()}
          className="mt-2 flex items-center gap-1 text-xs text-slate-500 hover:text-accent-blue transition-colors"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
          </svg>
          Download WAV
        </a>
      )}
    </div>
  )
}

export function TrackHistory() {
  const { tasks, currentTrack, setCurrentTrack } = useMusicStore()
  const completedTracks = tasks.filter((t) => t.status === 'completed')

  const handleSelect = (track: TaskResult) => {
    setCurrentTrack(currentTrack?.task_id === track.task_id ? null : track)
  }

  if (completedTracks.length === 0) {
    return (
      <div className="text-center py-8 text-slate-600 text-sm">
        No completed tracks yet.
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
          Track History
        </h2>
        <span className="text-xs font-mono text-slate-500">{completedTracks.length} tracks</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
        {completedTracks.map((track) => (
          <TrackCard
            key={track.task_id}
            track={track}
            isActive={currentTrack?.task_id === track.task_id}
            onSelect={handleSelect}
          />
        ))}
      </div>
    </div>
  )
}
