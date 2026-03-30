import React, { useEffect } from 'react'
import { useAudio } from '../../hooks/useAudio'
import type { TaskResult } from '../../api/client'

interface AudioPlayerProps {
  track?: TaskResult | null
}

function formatTime(secs: number): string {
  if (isNaN(secs) || !isFinite(secs)) return '0:00'
  const m = Math.floor(secs / 60)
  const s = Math.floor(secs % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function AudioPlayer({ track }: AudioPlayerProps) {
  const audioUrl = track?.audio_url
    ? `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${track.audio_url}`
    : undefined

  const { state, canvasRef, togglePlay, seek, setVolume, toggleMute } = useAudio(audioUrl)

  if (!track) {
    return (
      <div className="bg-bg-card border border-bg-border rounded-xl p-6 flex flex-col items-center justify-center min-h-[160px] text-center">
        <div className="text-4xl mb-3 opacity-30">♪</div>
        <p className="text-slate-500 text-sm">No track selected</p>
        <p className="text-slate-600 text-xs mt-1">Generate music or select a completed track</p>
      </div>
    )
  }

  const progressPct = state.duration > 0 ? (state.currentTime / state.duration) * 100 : 0

  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!state.duration) return
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const pct = x / rect.width
    seek(pct * state.duration)
  }

  const downloadUrl = audioUrl

  return (
    <div className="bg-bg-card border border-bg-border rounded-xl p-4 space-y-3">
      {/* Track info */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate">
            {track.metadata?.prompt || 'Generated Track'}
          </p>
          <div className="flex items-center gap-2 mt-0.5 flex-wrap">
            {track.metadata?.lora && (
              <span className="text-xs font-mono text-accent-purple bg-accent-purple/10 px-1.5 py-0.5 rounded">
                {track.metadata.lora}
              </span>
            )}
            {track.metadata?.generation_time && (
              <span className="text-xs text-slate-500 font-mono">
                {track.metadata.generation_time}s gen
              </span>
            )}
            {track.metadata?.gpu && (
              <span className="text-xs text-slate-500 font-mono">{track.metadata.gpu}</span>
            )}
          </div>
        </div>
        {downloadUrl && (
          <a
            href={downloadUrl}
            download={`musicforge-${track.task_id.slice(0, 8)}.wav`}
            className="flex-shrink-0 p-2 rounded-lg bg-bg-tertiary hover:bg-bg-border text-slate-400 hover:text-accent-blue transition-colors"
            title="Download"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3" />
            </svg>
          </a>
        )}
      </div>

      {/* Waveform canvas */}
      <div className="relative rounded-lg overflow-hidden bg-bg-secondary" style={{ height: 72 }}>
        <canvas
          ref={canvasRef}
          width={600}
          height={72}
          className="w-full h-full"
        />
        {state.isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-bg-secondary/80">
            <span className="inline-block w-5 h-5 border-2 border-accent-blue/30 border-t-accent-blue rounded-full animate-spin" />
          </div>
        )}
      </div>

      {/* Progress bar */}
      <div
        className="h-1.5 bg-bg-tertiary rounded-full cursor-pointer relative group"
        onClick={handleSeek}
      >
        <div
          className="h-full bg-gradient-to-r from-accent-blue to-accent-purple rounded-full transition-all"
          style={{ width: `${progressPct}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full shadow opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ left: `${progressPct}%`, transform: 'translate(-50%, -50%)' }}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center gap-3">
        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          disabled={!audioUrl || state.isLoading}
          className="w-10 h-10 rounded-full bg-accent-blue hover:bg-accent-blue/80 disabled:bg-bg-border disabled:text-slate-600 text-white flex items-center justify-center transition-all flex-shrink-0"
        >
          {state.isPlaying ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Time */}
        <span className="text-xs font-mono text-slate-500 tabular-nums">
          {formatTime(state.currentTime)} / {formatTime(state.duration)}
        </span>

        <div className="flex-1" />

        {/* Mute */}
        <button
          onClick={toggleMute}
          className="p-1.5 rounded text-slate-500 hover:text-slate-200 transition-colors"
        >
          {state.isMuted ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 5L6 9H2v6h4l5 4V5zM23 9l-6 6M17 9l6 6" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 5L6 9H2v6h4l5 4V5z" />
              <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" />
            </svg>
          )}
        </button>

        {/* Volume */}
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={state.isMuted ? 0 : state.volume}
          onChange={(e) => setVolume(Number(e.target.value))}
          className="w-20"
        />
      </div>
    </div>
  )
}
