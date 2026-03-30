import { create } from 'zustand'
import type { TaskResult, WorkerInfo } from '../api/client'

interface MusicStore {
  // Tasks
  tasks: TaskResult[]
  setTasks: (tasks: TaskResult[]) => void
  addOrUpdateTask: (task: TaskResult) => void
  removeTask: (taskId: string) => void

  // Currently playing track
  currentTrack: TaskResult | null
  setCurrentTrack: (track: TaskResult | null) => void

  // GPU workers
  workers: WorkerInfo[]
  setWorkers: (workers: WorkerInfo[]) => void

  // UI state
  isGenerating: boolean
  setIsGenerating: (v: boolean) => void

  activeTab: 'queue' | 'history'
  setActiveTab: (tab: 'queue' | 'history') => void
}

export const useMusicStore = create<MusicStore>((set, get) => ({
  tasks: [],
  setTasks: (tasks) => set({ tasks }),
  addOrUpdateTask: (task) => {
    const tasks = get().tasks
    const idx = tasks.findIndex((t) => t.task_id === task.task_id)
    if (idx >= 0) {
      const updated = [...tasks]
      updated[idx] = task
      set({ tasks: updated })
    } else {
      set({ tasks: [task, ...tasks] })
    }
  },
  removeTask: (taskId) =>
    set({ tasks: get().tasks.filter((t) => t.task_id !== taskId) }),

  currentTrack: null,
  setCurrentTrack: (track) => set({ currentTrack: track }),

  workers: [],
  setWorkers: (workers) => set({ workers }),

  isGenerating: false,
  setIsGenerating: (v) => set({ isGenerating: v }),

  activeTab: 'queue',
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
