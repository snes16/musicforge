import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { useMusicStore } from '../stores/musicStore'

export function useGPUStats(pollInterval = 2000) {
  const { setWorkers } = useMusicStore()

  const query = useQuery({
    queryKey: ['workers'],
    queryFn: () => api.getWorkers(),
    refetchInterval: pollInterval,
    staleTime: 1000,
  })

  useEffect(() => {
    if (query.data?.workers) {
      setWorkers(query.data.workers)
    }
  }, [query.data, setWorkers])

  return {
    workers: query.data?.workers ?? [],
    isLoading: query.isLoading,
    error: query.error,
    refetch: query.refetch,
  }
}
