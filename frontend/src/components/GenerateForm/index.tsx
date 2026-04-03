import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type GenerateRequest } from '../../api/client'
import { useGenerate } from '../../hooks/useGenerate'
import { useMusicStore } from '../../stores/musicStore'

const DURATION_MARKS = [30, 60, 90, 120, 180, 240, 300]

export function GenerateForm() {
  const { generate, isLoading } = useGenerate()
  const isGenerating = useMusicStore((s) => s.isGenerating)

  const [prompt, setPrompt] = useState('')
  const [lyrics, setLyrics] = useState(
    '[verse]\\nFirst verse line\\nSecond verse line\\n\\n[chorus]\\nMain hook line\\nRepeatable chorus line',
  )
  const [duration, setDuration] = useState(60)
  const [loraName, setLoraName] = useState('')
  const [stylePreset, setStylePreset] = useState('')

  const { data: modelsData } = useQuery({
    queryKey: ['models'],
    queryFn: api.getModels,
    staleTime: 30000,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || !lyrics.trim()) return

    const req: GenerateRequest = {
      prompt: prompt.trim(),
      lyrics: lyrics.trim(),
      duration,
    }
    if (loraName) req.lora_name = loraName
    if (stylePreset) req.style_preset = stylePreset

    generate(req)
  }

  const handlePresetSelect = (presetId: string) => {
    const presets = modelsData?.style_presets ?? []

    const stripLeadingPresetHint = (value: string): string => {
      let stripped = value.trim()
      for (const item of presets) {
        const hint = item.prompt_hint.trim()
        if (!hint) continue
        const withComma = `${hint}, `
        if (stripped.toLowerCase().startsWith(withComma.toLowerCase())) {
          stripped = stripped.slice(withComma.length).trim()
          break
        }
        if (stripped.toLowerCase() === hint.toLowerCase()) {
          stripped = ''
          break
        }
      }
      return stripped
    }

    setStylePreset(presetId)
    setPrompt((current) => {
      const basePrompt = stripLeadingPresetHint(current)
      if (!presetId) return basePrompt

      const selected = presets.find((p) => p.id === presetId)
      if (!selected) return current

      return basePrompt ? `${selected.prompt_hint}, ${basePrompt}` : selected.prompt_hint
    })
  }

  const formatDuration = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return s === 0 ? `${m}m` : `${m}m ${s}s`
  }

  const busy = isLoading || isGenerating
  const hasLyricsSections =
    lyrics.toLowerCase().includes('[verse]') && lyrics.toLowerCase().includes('[chorus]')

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Prompt */}
      <div>
        <label className="block text-xs font-mono text-slate-400 mb-1.5 uppercase tracking-wider">
          Music Prompt
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="indie pop, female vocals, dreamy atmosphere, reverb guitar..."
          rows={3}
          maxLength={1000}
          required
          className="w-full bg-bg-secondary border border-bg-border rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-500 resize-none focus:border-accent-blue transition-colors"
        />
        <div className="text-right text-xs text-slate-600 mt-1">{prompt.length}/1000</div>
      </div>

      {/* Style Presets */}
      {modelsData?.style_presets && (
        <div>
          <label className="block text-xs font-mono text-slate-400 mb-1.5 uppercase tracking-wider">
            Style Preset
          </label>
          <div className="flex flex-wrap gap-1.5">
            {modelsData.style_presets.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => handlePresetSelect(preset.id === stylePreset ? '' : preset.id)}
                className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
                  stylePreset === preset.id
                    ? 'bg-accent-blue text-white'
                    : 'bg-bg-tertiary text-slate-400 hover:text-slate-200 hover:bg-bg-border'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Duration */}
      <div>
        <div className="flex justify-between items-center mb-1.5">
          <label className="text-xs font-mono text-slate-400 uppercase tracking-wider">
            Duration
          </label>
          <span className="text-sm font-mono text-accent-blue">{formatDuration(duration)}</span>
        </div>
        <input
          type="range"
          min={30}
          max={300}
          step={30}
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-slate-600 mt-1 font-mono">
          {DURATION_MARKS.map((m) => (
            <span key={m}>{formatDuration(m)}</span>
          ))}
        </div>
      </div>

      {/* LoRA Select */}
      <div>
        <label className="block text-xs font-mono text-slate-400 mb-1.5 uppercase tracking-wider">
          Artist Style (LoRA)
        </label>
        <select
          value={loraName}
          onChange={(e) => setLoraName(e.target.value)}
          className="w-full bg-bg-secondary border border-bg-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:border-accent-blue transition-colors"
        >
          <option value="">Base Model (no LoRA)</option>
          {modelsData?.loras.map((lora) => (
            <option key={lora.name} value={lora.name}>
              {lora.name} {lora.file_size_mb ? `(${lora.file_size_mb} MB)` : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Lyrics (required) */}
      <div>
        <label className="block text-xs font-mono text-slate-400 mb-1.5 uppercase tracking-wider">
          Lyrics (Required)
        </label>
        <textarea
          value={lyrics}
          onChange={(e) => setLyrics(e.target.value)}
          placeholder={`[verse]\nYour verse lyrics here\n\n[chorus]\nChorus text`}
          rows={8}
          maxLength={5000}
          required
          className="w-full bg-bg-secondary border border-bg-border rounded-lg px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 resize-none font-mono focus:border-accent-purple transition-colors"
        />
        <div className="mt-1 flex items-center justify-between text-xs font-mono">
          <span className={hasLyricsSections ? 'text-status-completed' : 'text-status-failed'}>
            Must contain [verse] and [chorus]
          </span>
          <span className="text-slate-600">{lyrics.length}/5000</span>
        </div>
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={busy || !prompt.trim() || !lyrics.trim() || !hasLyricsSections}
        className={`w-full py-3 rounded-lg font-semibold text-sm transition-all ${
          busy || !prompt.trim() || !lyrics.trim() || !hasLyricsSections
            ? 'bg-bg-border text-slate-500 cursor-not-allowed'
            : 'bg-gradient-to-r from-accent-blue to-accent-purple text-white hover:opacity-90 active:scale-[0.99]'
        }`}
      >
        {busy ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Generating...
          </span>
        ) : (
          'Generate Music'
        )}
      </button>
    </form>
  )
}
