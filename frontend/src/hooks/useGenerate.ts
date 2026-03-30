import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { api, type GenerateRequest, type TaskResult } from '../api/client'
import { useMusicStore } from '../stores/musicStore'

export function useGenerate() {
  const queryClient = useQueryClient()
  const { addOrUpdateTask, setIsGenerating } = useMusicStore()
  const pollingRefs = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())

  const startPolling = (taskId: string) => {
    if (pollingRefs.current.has(taskId)) return

    const intervalId = setInterval(async () => {
      try {
        const task = await api.getTask(taskId)
        addOrUpdateTask(task)
        queryClient.setQueryData(['task', taskId], task)

        if (task.status === 'completed' || task.status === 'failed') {
          stopPolling(taskId)
          if (task.status === 'completed') {
            setIsGenerating(false)
          }
        }
      } catch (err) {
        console.error(`Polling error for task ${taskId}:`, err)
      }
    }, 2000)

    pollingRefs.current.set(taskId, intervalId)
  }

  const stopPolling = (taskId: string) => {
    const id = pollingRefs.current.get(taskId)
    if (id) {
      clearInterval(id)
      pollingRefs.current.delete(taskId)
    }
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      pollingRefs.current.forEach((id) => clearInterval(id))
      pollingRefs.current.clear()
    }
  }, [])

  const mutation = useMutation({
    mutationFn: (req: GenerateRequest) => api.generate(req),
    onSuccess: (data) => {
      setIsGenerating(true)
      // Add as queued immediately
      const newTask: TaskResult = {
        task_id: data.task_id,
        status: 'queued',
        progress: 0,
      }
      addOrUpdateTask(newTask)
      startPolling(data.task_id)
    },
    onError: (err) => {
      setIsGenerating(false)
      console.error('Generation error:', err)
    },
  })

  return {
    generate: mutation.mutate,
    generateAsync: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error,
    data: mutation.data,
    startPolling,
    stopPolling,
  }
}
