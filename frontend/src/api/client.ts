import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Types mirroring backend schemas
export interface GenerateRequest {
  prompt: string
  lyrics?: string
  duration: number
  lora_name?: string
  style_preset?: string
}

export interface GenerateResponse {
  task_id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  estimated_seconds: number
  position_in_queue: number
}

export interface TaskMetadata {
  model?: string
  lora?: string
  generation_time?: number
  gpu?: string
  prompt?: string
  duration?: number
}

export type TaskStatus = 'queued' | 'processing' | 'completed' | 'failed'

export interface TaskResult {
  task_id: string
  status: TaskStatus
  progress: number
  audio_url?: string
  duration?: number
  metadata?: TaskMetadata
  error?: string
  created_at?: string
  updated_at?: string
}

export interface WorkerInfo {
  id: string
  gpu: string
  vram_total: number
  vram_used: number
  status: 'idle' | 'busy' | 'offline'
  tasks_completed: number
  temperature?: number
  current_task?: string
}

export interface WorkersResponse {
  workers: WorkerInfo[]
}

export interface LoRAModel {
  name: string
  description?: string
  file_size_mb?: number
}

export interface StylePreset {
  id: string
  label: string
  prompt_hint: string
}

export interface ModelsResponse {
  loras: LoRAModel[]
  style_presets: StylePreset[]
  base_model: string
}

export interface TaskListResponse {
  tasks: TaskResult[]
  total: number
}

// API functions
export const api = {
  generate: (req: GenerateRequest) =>
    apiClient.post<GenerateResponse>('/api/generate', req).then((r) => r.data),

  getTask: (taskId: string) =>
    apiClient.get<TaskResult>(`/api/generate/${taskId}`).then((r) => r.data),

  listTasks: (limit = 50, offset = 0) =>
    apiClient.get<TaskListResponse>('/api/tasks', { params: { limit, offset } }).then((r) => r.data),

  deleteTask: (taskId: string) =>
    apiClient.delete(`/api/tasks/${taskId}`).then((r) => r.data),

  getModels: () =>
    apiClient.get<ModelsResponse>('/api/models').then((r) => r.data),

  getWorkers: () =>
    apiClient.get<WorkersResponse>('/workers').then((r) => r.data),

  getHealth: () =>
    apiClient.get('/health').then((r) => r.data),
}

export default apiClient
