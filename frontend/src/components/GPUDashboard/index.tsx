import React from 'react'
import { useGPUStats } from '../../hooks/useGPUStats'
import type { WorkerInfo } from '../../api/client'

function GPUCard({ worker }: { worker: WorkerInfo }) {
  const vramPct = worker.vram_total > 0 ? (worker.vram_used / worker.vram_total) * 100 : 0

  const statusConfig = {
    idle: { label: 'IDLE', color: 'text-status-idle', dotColor: 'bg-status-idle' },
    busy: { label: 'BUSY', color: 'text-status-busy', dotColor: 'bg-status-busy' },
    offline: { label: 'OFFLINE', color: 'text-status-offline', dotColor: 'bg-status-offline' },
  }
  const { label, color, dotColor } = statusConfig[worker.status] || statusConfig.offline

  const vramBarColor =
    vramPct > 85 ? 'from-red-500 to-red-600' :
    vramPct > 60 ? 'from-yellow-500 to-amber-500' :
    'from-accent-blue to-accent-purple'

  return (
    <div className="bg-bg-card border border-bg-border rounded-xl p-4 min-w-[200px] flex-1">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${dotColor} ${worker.status === 'busy' ? 'animate-pulse' : ''}`} />
          <span className={`text-xs font-mono font-semibold ${color}`}>{label}</span>
        </div>
        <span className="text-xs font-mono text-slate-500">{worker.id}</span>
      </div>

      {/* GPU Name */}
      <p className="text-sm font-semibold text-slate-200 mb-3 truncate">{worker.gpu}</p>

      {/* VRAM */}
      <div className="space-y-1.5">
        <div className="flex justify-between text-xs font-mono text-slate-500">
          <span>VRAM</span>
          <span>
            {(worker.vram_used / 1024).toFixed(1)} / {(worker.vram_total / 1024).toFixed(1)} GB
          </span>
        </div>
        <div className="h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className={`h-full bg-gradient-to-r ${vramBarColor} rounded-full transition-all duration-1000`}
            style={{ width: `${vramPct}%` }}
          />
        </div>
        <div className="text-right text-xs font-mono text-slate-600">{vramPct.toFixed(0)}%</div>
      </div>

      {/* Temperature */}
      {worker.temperature !== undefined && worker.temperature !== null && (
        <div className="flex justify-between items-center mt-2 text-xs font-mono text-slate-500">
          <span>Temp</span>
          <span className={worker.temperature > 80 ? 'text-status-failed' : worker.temperature > 65 ? 'text-status-busy' : 'text-status-idle'}>
            {worker.temperature.toFixed(0)}°C
          </span>
        </div>
      )}

      {/* Tasks completed */}
      <div className="flex justify-between items-center mt-1.5 text-xs font-mono text-slate-500">
        <span>Tasks done</span>
        <span>{worker.tasks_completed}</span>
      </div>

      {/* Current task */}
      {worker.current_task && (
        <div className="mt-2 text-xs font-mono text-accent-blue truncate">
          #{worker.current_task.slice(0, 8)}
        </div>
      )}
    </div>
  )
}

export function GPUDashboard() {
  const { workers, isLoading } = useGPUStats(2000)

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider font-mono">
          GPU Workers
        </h2>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-status-idle animate-pulse" />
          <span className="text-xs font-mono text-slate-500">
            {workers.filter((w) => w.status !== 'offline').length}/{workers.length} online
          </span>
        </div>
      </div>

      {isLoading && workers.length === 0 ? (
        <div className="flex gap-3">
          {[0].map((i) => (
            <div key={i} className="bg-bg-card border border-bg-border rounded-xl p-4 flex-1 animate-pulse">
              <div className="h-3 bg-bg-tertiary rounded mb-3 w-2/3" />
              <div className="h-4 bg-bg-tertiary rounded mb-3" />
              <div className="h-1.5 bg-bg-tertiary rounded" />
            </div>
          ))}
        </div>
      ) : workers.length === 0 ? (
        <div className="bg-bg-card border border-bg-border rounded-xl p-4 text-center text-sm text-slate-500">
          No GPU workers detected. Set <span className="font-mono text-accent-blue">MOCK_GPU=true</span> for development.
        </div>
      ) : (
        <div className="flex gap-3 flex-wrap">
          {workers.map((worker) => (
            <GPUCard key={worker.id} worker={worker} />
          ))}
        </div>
      )}
    </div>
  )
}
