import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, type TaskResult, type TaskStatus } from '../../api/client'
import { useMusicStore } from '../../stores/musicStore'

function StatusBadge({ status }: { status: TaskStatus }) {
  const config = {
    queued: { label: 'Queued', cls: 'text-slate-400 bg-slate-400/10' },
    processing: { label: 'Processing', cls: 'text-accent-blue bg-accent-blue/10' },
    completed: { label: 'Done', cls: 'text-status-completed bg-status-completed/10' },
    failed: { label: 'Failed', cls: 'text-status-failed bg-status-failed/10' },
  }
  const { label, cls } = config[status] || config.queued

  return (
    <span className={`text-xs font-mono px-2 py-0.5 rounded-full ${cls}`}>
      {status === 'processing' && (
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-accent-blue mr-1 animate-pulse" />
      )}
      {label}
    </span>
  )
}

function TaskCard({ task }: { task: TaskResult }) {
  const { setCurrentTrack, currentTrack } = useMusicStore()
  const isActive = currentTrack?.task_id === task.task_id

  const handleClick = () => {
    if (task.status === 'completed') {
      setCurrentTrack(isActive ? null : task)
    }
  }

  return (
    <div
      onClick={handleClick}
      className={`bg-bg-card border rounded-lg p-3 transition-all animate-slide-up ${
        task.status === 'completed'
          ? 'cursor-pointer hover:border-accent-blue/50'
          : 'cursor-default'
      } ${isActive ? 'border-accent-blue/70' : 'border-bg-border'}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-mono text-slate-500 truncate">
          #{task.task_id.slice(0, 8)}
        </span>
        <StatusBadge status={task.status} />
      </div>

      {/* Prompt */}
      <p className="text-sm text-slate-300 truncate mb-2">
        {task.metadata?.prompt || 'Unknown prompt'}
      </p>

      {/* Progress bar for processing */}
      {(task.status === 'processing' || task.status === 'queued') && (
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

  // Periodically refresh task list from server
  useQuery({
    queryKey: ['tasks-list'],
    queryFn: async () => {
      const data = await api.listTasks(50, 0)
      setTasks(data.tasks)
      return data
    },
    refetchInterval: 3000,
  })

  const activeTasks = tasks.filter((t) => t.status === 'queued' || t.status === 'processing')
  const doneTasks = tasks.filter((t) => t.status === 'completed' || t.status === 'failed')

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
              <TaskCard key={task.task_id} task={task} />
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
              <TaskCard key={task.task_id} task={task} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
