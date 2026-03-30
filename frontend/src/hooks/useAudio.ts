import { useRef, useEffect, useCallback, useState } from 'react'

export interface AudioState {
  isPlaying: boolean
  currentTime: number
  duration: number
  volume: number
  isMuted: boolean
  isLoading: boolean
}

export function useAudio(audioUrl?: string) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const sourceRef = useRef<MediaElementAudioSourceNode | null>(null)
  const animFrameRef = useRef<number | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  const [state, setState] = useState<AudioState>({
    isPlaying: false,
    currentTime: 0,
    duration: 0,
    volume: 1,
    isMuted: false,
    isLoading: false,
  })

  // Initialize audio element
  useEffect(() => {
    if (!audioUrl) return

    const audio = new Audio()
    audio.crossOrigin = 'anonymous'
    audio.preload = 'metadata'
    audioRef.current = audio

    setState((s) => ({ ...s, isLoading: true }))
    audio.src = audioUrl

    audio.addEventListener('loadedmetadata', () => {
      setState((s) => ({ ...s, duration: audio.duration, isLoading: false }))
    })

    audio.addEventListener('timeupdate', () => {
      setState((s) => ({ ...s, currentTime: audio.currentTime }))
    })

    audio.addEventListener('ended', () => {
      setState((s) => ({ ...s, isPlaying: false, currentTime: 0 }))
    })

    audio.addEventListener('error', () => {
      setState((s) => ({ ...s, isLoading: false }))
    })

    return () => {
      audio.pause()
      audio.src = ''
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
      audioRef.current = null
    }
  }, [audioUrl])

  // Setup Web Audio API analyser for waveform
  const setupAnalyser = useCallback(() => {
    if (!audioRef.current) return
    if (audioContextRef.current) return // already set up

    const ctx = new AudioContext()
    audioContextRef.current = ctx

    const analyser = ctx.createAnalyser()
    analyser.fftSize = 2048
    analyserRef.current = analyser

    const source = ctx.createMediaElementSource(audioRef.current)
    source.connect(analyser)
    analyser.connect(ctx.destination)
    sourceRef.current = source
  }, [])

  // Draw waveform on canvas
  const drawWaveform = useCallback(() => {
    const canvas = canvasRef.current
    const analyser = analyserRef.current
    if (!canvas || !analyser) return

    const ctx2d = canvas.getContext('2d')
    if (!ctx2d) return

    const bufferLength = analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw)
      analyser.getByteTimeDomainData(dataArray)

      const { width, height } = canvas
      ctx2d.fillStyle = '#12121a'
      ctx2d.fillRect(0, 0, width, height)

      ctx2d.lineWidth = 2
      ctx2d.strokeStyle = '#3b82f6'
      ctx2d.shadowBlur = 8
      ctx2d.shadowColor = '#3b82f6'
      ctx2d.beginPath()

      const sliceWidth = width / bufferLength
      let x = 0

      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0
        const y = (v * height) / 2

        if (i === 0) {
          ctx2d.moveTo(x, y)
        } else {
          ctx2d.lineTo(x, y)
        }
        x += sliceWidth
      }

      ctx2d.lineTo(width, height / 2)
      ctx2d.stroke()
    }

    draw()
  }, [])

  const play = useCallback(async () => {
    const audio = audioRef.current
    if (!audio) return

    setupAnalyser()
    if (audioContextRef.current?.state === 'suspended') {
      await audioContextRef.current.resume()
    }
    await audio.play()
    setState((s) => ({ ...s, isPlaying: true }))
    drawWaveform()
  }, [setupAnalyser, drawWaveform])

  const pause = useCallback(() => {
    audioRef.current?.pause()
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    setState((s) => ({ ...s, isPlaying: false }))
  }, [])

  const togglePlay = useCallback(() => {
    if (state.isPlaying) {
      pause()
    } else {
      play()
    }
  }, [state.isPlaying, play, pause])

  const seek = useCallback((time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time
      setState((s) => ({ ...s, currentTime: time }))
    }
  }, [])

  const setVolume = useCallback((vol: number) => {
    if (audioRef.current) {
      audioRef.current.volume = vol
      setState((s) => ({ ...s, volume: vol, isMuted: vol === 0 }))
    }
  }, [])

  const toggleMute = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.muted = !audioRef.current.muted
      setState((s) => ({ ...s, isMuted: audioRef.current!.muted }))
    }
  }, [])

  return {
    state,
    canvasRef,
    play,
    pause,
    togglePlay,
    seek,
    setVolume,
    toggleMute,
  }
}
