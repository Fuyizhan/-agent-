import { Check, Circle, Loader2, AlertCircle } from 'lucide-react'
import type { StepEvent } from '../types'

export interface StepDef {
  key: string
  label: string
}

interface Props {
  steps: StepDef[]
  stepLog: StepEvent[]
  currentStep: string
  progress: number
  error?: string
}

export default function StepIndicator({ steps, stepLog, currentStep, progress, error }: Props) {
  const eventByStep = new Map<string, StepEvent>()
  for (const e of stepLog) {
    eventByStep.set(e.step, e)
  }

  const pct = Math.round(Math.max(0, Math.min(1, progress)) * 100)

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text">多Agent流水线审查中</h3>
          <span className="text-sm text-muted font-mono">{pct}%</span>
        </div>
        <div className="h-1.5 bg-surface-3 rounded-full overflow-hidden mb-6">
          <div
            className="h-full bg-accent-cyan transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>

        <ol className="space-y-4">
          {steps.map((s, idx) => {
            const ev = eventByStep.get(s.key)
            const isRunning = currentStep.split(',').includes(s.key) || ev?.status === 'running'
            const isDone = ev?.status === 'done'
            const isError = ev?.status === 'error'
            const isPending = !ev && !isRunning

            let Icon = Circle
            let iconClass = 'text-muted'
            let bgClass = 'bg-surface-3'
            let labelClass = 'text-muted'
            let msg = ''
            let duration = ''

            if (isDone) {
              Icon = Check
              iconClass = 'text-accent-green'
              bgClass = 'bg-accent-green/10'
              labelClass = 'text-text'
              msg = ev?.message || '完成'
              if (ev?.started_at && ev.finished_at) {
                const ms = new Date(ev.finished_at).getTime() - new Date(ev.started_at).getTime()
                duration = `${(ms / 1000).toFixed(1)}s`
              }
            } else if (isError) {
              Icon = AlertCircle
              iconClass = 'text-accent-red'
              bgClass = 'bg-accent-red/10'
              labelClass = 'text-accent-red'
              msg = ev?.message || '失败'
            } else if (isRunning) {
              Icon = Loader2
              iconClass = 'text-accent-cyan animate-spin'
              bgClass = 'bg-accent-cyan/10'
              labelClass = 'text-accent-cyan'
              msg = ev?.message || '进行中...'
            } else {
              msg = '等待中'
            }

            return (
              <li key={s.key} className="flex items-start gap-3">
                <div className={`flex-shrink-0 w-8 h-8 rounded-full ${bgClass} flex items-center justify-center border border-surface-3`}>
                  <Icon className={`w-4 h-4 ${iconClass}`} />
                </div>
                <div className="flex-1 pt-1">
                  <div className="flex items-baseline justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted">{idx + 1}.</span>
                      <span className={`text-sm font-medium ${labelClass}`}>{s.label}</span>
                    </div>
                    {duration && <span className="text-xs font-mono text-muted">{duration}</span>}
                  </div>
                  <p className={`text-xs mt-0.5 ${isError ? 'text-accent-red' : 'text-muted'}`}>{msg}</p>
                </div>
              </li>
            )
          })}
        </ol>

        {error && (
          <div className="mt-5 p-3 bg-accent-red/10 border border-accent-red/20 rounded-lg">
            <p className="text-sm text-accent-red">错误：{error}</p>
          </div>
        )}
      </div>
    </div>
  )
}
