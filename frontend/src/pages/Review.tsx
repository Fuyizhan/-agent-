import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import StepIndicator from '../components/StepIndicator'
import type { DetailedReview, StepEvent } from '../types'

const PIPELINE_STEPS = [
  { key: 'clause_extraction', label: '条款提取' },
  { key: 'risk_identification', label: '风险识别' },
  { key: 'compliance_check', label: '合规检查' },
  { key: 'suggestion', label: '修改建议' },
]

export default function Review() {
  const [file, setFile] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [trackingId, setTrackingId] = useState<string | null>(null)
  const [stepLog, setStepLog] = useState<StepEvent[]>([])
  const [currentStep, setCurrentStep] = useState('')
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)
  const pollTimer = useRef<number | null>(null)
  const navigate = useNavigate()

  const stopPolling = useCallback(() => {
    if (pollTimer.current !== null) {
      window.clearTimeout(pollTimer.current)
      pollTimer.current = null
    }
  }, [])

  useEffect(() => () => stopPolling(), [stopPolling])

  const poll = useCallback((reviewId: string) => {
    const tick = async () => {
      try {
        const data: DetailedReview = await api.getReview(reviewId)
        setStepLog(data.step_log)
        setCurrentStep(data.current_step)
        setProgress(data.progress)
        if (data.status === 'completed') {
          stopPolling()
          navigate(`/review/${reviewId}`)
          return
        }
        if (data.status === 'failed') {
          stopPolling()
          setSubmitting(false)
          setError(data.errors.at(-1) || '审查失败')
          return
        }
        pollTimer.current = window.setTimeout(tick, 1000)
      } catch (err) {
        stopPolling()
        setSubmitting(false)
        setError(err instanceof Error ? err.message : '查询进度失败')
      }
    }
    void tick()
  }, [navigate, stopPolling])

  const handleSubmit = async () => {
    if (!file) return
    setSubmitting(true)
    setError('')
    try {
      const task = await api.uploadReview(file)
      setTrackingId(task.review_id)
      poll(task.review_id)
    } catch (err) {
      setSubmitting(false)
      setError(err instanceof Error ? err.message : '上传失败')
    }
  }

  const reset = () => {
    stopPolling()
    setTrackingId(null)
    setSubmitting(false)
    setFile(null)
    setError('')
    setProgress(0)
    setStepLog([])
    if (fileRef.current) fileRef.current.value = ''
  }

  if (trackingId) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">合同审查</h2>
          <button onClick={reset} className="text-sm text-muted hover:text-text">
            返回重新上传
          </button>
        </div>
        <StepIndicator steps={PIPELINE_STEPS} stepLog={stepLog} currentStep={currentStep} progress={progress} error={error} />
        {error && <div className="text-center"><button onClick={reset} className="px-4 py-2 bg-surface-3 rounded-lg text-sm">重新上传</button></div>}
      </div>
    )
  }

  if (submitting) return <LoadingSpinner text="正在上传合同..." />

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h2 className="text-2xl font-bold">合同审查</h2>
        <p className="text-sm text-muted mt-1">上传单个合同，系统将依次执行四个 Agent 并生成审查报告。</p>
      </div>
      <div className="bg-surface-2 border border-surface-3 rounded-xl p-6">
        <div className="border-2 border-dashed border-surface-4 rounded-xl p-10 text-center hover:border-accent-cyan transition">
          <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="hidden"
            onChange={e => setFile(e.target.files?.[0] || null)} />
          <button onClick={() => fileRef.current?.click()} className="text-accent-cyan hover:underline text-sm font-medium">
            选择合同文件
          </button>
          <p className="text-xs text-muted mt-2">支持 PDF、DOCX、TXT，最大 20 MB</p>
          {file && <p className="text-sm text-accent-green mt-4">已选择：{file.name}</p>}
        </div>
        {error && <p className="mt-4 text-sm text-accent-red break-all">{error}</p>}
        <div className="mt-5 flex justify-end">
          <button onClick={handleSubmit} disabled={!file}
            className="px-6 py-2.5 bg-accent-cyan text-white rounded-lg text-sm font-medium disabled:opacity-50">
            上传并开始审查
          </button>
        </div>
      </div>
      <div className="bg-surface-2 border border-surface-3 rounded-xl p-4 text-xs text-muted">
        未配置模型 API Key 时仍可运行，系统会自动使用规则和启发式结果完成审查，并在报告中标注降级步骤。
      </div>
    </div>
  )
}
