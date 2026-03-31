import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type TaskResult, type TaskStatus } from '../../api/client'
import { useMusicStore } from '../../stores/musicStore'

function StatusBadge({ status }: { status: TaskStatus }) {
  const config: Record<TaskStatus, { label: string; cls: string }> = {
    queued:     { label: 'Queued',      cls: 'text-slate-400 bg-slate-400/10' },
    processing: { label: 'Processing',  cls: 'text-accent-blue bg-accent-blue/10' },
    completed:  { label: 'Done',        cls: 'text-status-completed bg-status-completed/10' },
    failed:     { label: 'Failed',      cls: 'text-status-failed bg-status-failed/10' },
    cancelled:  { label: 'Cancelled',   cls: 'text-slate-500 bg-slate-500/10' },
  }
  const { label, cls } = config[status] ?? config.queued

  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${cls}`}>
      {status === 'processing' && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-blue mr-1 animate-pulse" />
      )}
      {label}
    </span>
  )
}

function CancelButton({ taskId, onCancel }: { taskId: string; onCancel: () => void }) {
  const [loading, setLoading] = React.useState(false)

  const handleCancel = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setLoading(true)
    try {
      await api.deleteTask(taskId)
      onCancel()
    } catch {
      // ignore — the task list will refresh anyway
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      onClick={handleCancel}
      disabled={loading}
      title="Cancel task"
      className="p-1 rounded text-slate-600 hover:text-status-failed hover:bg-status-failed/10 transition-colors disabled:opacity-40"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
        <path d="M18 6 6 18M6 6l12 12" />
      </svg>
    </button>
  )
}

function TaskCard({ task, onCancelled }: { task: TaskResult; onCancelled: () => void }) {
  const { setCurrentTrack, currentTrack } = useMusicStore()
  const isActive = currentTrack?.task_id === task.task_id
  const isActive_ = task.status === 'queued' || task.status === 'processing'

  const handleClick = () => {
    if (task.status === 'completed') {
      setCurrentTrack(isActive ? null : task)
    }
  }

  return (
    <div
      onClick={handleClick}
      className={`glass-card rounded-lg p-3 transition-all animate-slide-up ${
        task.status === 'completed'
          ? 'cursor-pointer hover:border-accent-blue/50'
          : 'cursor-default'
      } ${isActive ? 'border-accent-blue/70' : ''}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-mono text-slate-500 truncate">
          #{task.task_id.slice(0, 8)}
        </span>
        <div className="flex items-center gap-1.5">
          <StatusBadge status={task.status} />
          {isActive_ && <CancelButton taskId={task.task_id} onCancel={onCancelled} />}
        </div>
      </div>

      {/* Prompt */}
      <p className="text-sm text-slate-300 truncate mb-2">
        {task.metadata?.prompt || 'Unknown prompt'}
      </p>

      {/* Progress bar */}
      {isActive_ && (
        <div className="h-1 bg-bg-tertiary rounded-full overflow-hidden mb-2">
          <div
            className="h-full bg-gradient-to-r from-accent-blue to-accent-purple transition-all duration-500"
            style={{ width: `${task.progress || 0}%` }}
          />
        </div>
      )}

      {/* Meta row */}
      <div className="flex items-center gap-3 text-xs font-mono text-slate-500 flex-wrap">
        {task.duration && <span>{task.duration}s</span>}
        {task.metadata?.lora && (
          <span className="text-accent-purple">{task.metadata.lora}</span>
        )}
        {task.metadata?.generation_time && (
          <span>{task.metadata.generation_time}s gen</span>
        )}
        {task.status === 'processing' && (
          <span className="text-accent-blue">{task.progress || 0}%</span>
        )}
        {task.status === 'failed' && task.error && (
          <span className="text-status-failed truncate">{task.error}</span>
        )}
        {task.status === 'completed' && (
          <span className="text-status-completed ml-auto">Click to play</span>
        )}
      </div>
    </div>
  )
}

export function TaskQueue() {
  const { tasks, setTasks } = useMusicStore()
  const queryClient = useQueryClient()

  const { refetch } = useQuery({
    queryKey: ['tasks-list'],
    queryFn: async () => {
      const data = await api.listTasks(50, 0)
      setTasks(data.tasks)
      return data
    },
    refetchInterval: 2000,
  })

  const activeTasks = tasks.filter((t) => t.status === 'queued' || t.status === 'processing')
  const doneTasks = tasks.filter(
    (t) => t.status === 'completed' || t.status === 'failed' || t.status === 'cancelled',
  )

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
          Task Queue
        </h2>
        <span className="text-xs font-mono text-slate-500">
          {activeTasks.length} active
        </span>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {tasks.length === 0 && (
          <div className="text-center py-8 text-slate-600 text-sm">
            No tasks yet. Generate some music!
          </div>
        )}

        {activeTasks.length > 0 && (
          <div className="space-y-2">
            {activeTasks.map((task) => (
              <TaskCard key={task.task_id} task={task} onCancelled={() => refetch()} />
            ))}
          </div>
        )}

        {doneTasks.length > 0 && (
          <div className="space-y-2">
            {activeTasks.length > 0 && (
              <div className="text-xs font-mono text-slate-600 uppercase tracking-wider pt-2">
                Completed
              </div>
            )}
            {doneTasks.map((task) => (
              <TaskCard key={task.task_id} task={task} onCancelled={() => refetch()} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
