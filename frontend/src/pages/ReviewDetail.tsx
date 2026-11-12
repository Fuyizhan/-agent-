import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Download, FileText } from 'lucide-react'
import { api } from '../api/client'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge from '../components/StatusBadge'
import StepIndicator from '../components/StepIndicator'
import type { DetailedReview } from '../types'

const STEPS = [
  { key: 'clause_extraction', label: '条款提取' },
  { key: 'risk_identification', label: '风险识别' },
  { key: 'compliance_check', label: '合规检查' },
  { key: 'suggestion', label: '修改建议' },
]

const RISK_MAP: Record<string, { label: string; variant: 'success' | 'warning' | 'error' | 'info' }> = {
  high: { label: '高风险', variant: 'error' },
  medium: { label: '中风险', variant: 'warning' },
  low: { label: '低风险', variant: 'info' },
  none: { label: '无风险', variant: 'success' },
}

const COMPLIANCE_MAP: Record<string, { label: string; variant: 'success' | 'warning' | 'error' }> = {
  compliant: { label: '合规', variant: 'success' },
  non_compliant: { label: '不合规', variant: 'error' },
  needs_review: { label: '待复核', variant: 'warning' },
}

type Tab = 'clauses' | 'risks' | 'compliance' | 'suggestions'

export default function ReviewDetail() {
  const { id = '' } = useParams()
  const [data, setData] = useState<DetailedReview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<Tab>('clauses')

  const load = useCallback(async () => {
    try {
      const review = await api.getReview(id)
      setData(review)
      setError('')
      return review
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载失败')
      return null
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    let timer: number | null = null
    const tick = async () => {
      const review = await load()
      if (review && (review.status === 'pending' || review.status === 'in_progress')) {
        timer = window.setTimeout(tick, 1000)
      }
    }
    void tick()
    return () => {
      if (timer !== null) window.clearTimeout(timer)
    }
  }, [load])

  const handleDownload = async () => {
    try {
      await api.downloadReport(id)
    } catch (err) {
      setError(err instanceof Error ? err.message : '下载失败')
    }
  }

  if (loading) return <LoadingSpinner text="加载审查报告..." />
  if (!data) return <div className="text-center py-20 text-accent-red">{error || '审查记录不存在'}</div>

  if (data.status === 'pending' || data.status === 'in_progress') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4"><Link to="/review" className="text-muted hover:text-text">← 返回</Link><h2 className="text-2xl font-bold">审查进行中</h2></div>
        <StepIndicator steps={STEPS} stepLog={data.step_log} currentStep={data.current_step} progress={data.progress} />
      </div>
    )
  }

  const risk = RISK_MAP[data.overall_risk_level] || RISK_MAP.none
  const compliance = COMPLIANCE_MAP[data.overall_compliance] || COMPLIANCE_MAP.needs_review
  const tabs: { key: Tab; label: string }[] = [
    { key: 'clauses', label: `条款 (${data.clauses.length})` },
    { key: 'risks', label: `风险 (${data.risk_findings.length})` },
    { key: 'compliance', label: `合规 (${data.compliance_findings.length})` },
    { key: 'suggestions', label: `建议 (${data.suggestions.length})` },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <Link to="/review" className="text-muted hover:text-text">← 返回</Link>
        <h2 className="text-2xl font-bold">审查报告</h2>
        <StatusBadge label={risk.label} variant={risk.variant} />
        <StatusBadge label={compliance.label} variant={compliance.variant} />
        <div className="flex-1" />
        <button onClick={handleDownload} className="flex items-center gap-2 px-4 py-2 bg-accent-cyan text-white rounded-lg text-sm">
          <Download className="w-4 h-4" /> 下载 PDF
        </button>
      </div>

      {data.status === 'failed' && (
        <div className="p-4 rounded-xl bg-accent-red/10 border border-accent-red/20 text-sm text-accent-red">
          审查失败：{data.errors.at(-1) || '未知错误'}
        </div>
      )}
      {data.has_quality_issues && data.status === 'completed' && (
        <div className="p-4 rounded-xl bg-accent-amber/10 border border-accent-amber/20 text-sm text-accent-amber">
          当前报告包含降级结果：{data.degraded_steps.length ? data.degraded_steps.join('、') : data.warnings.at(-1)}
        </div>
      )}
      {error && <div className="p-3 rounded-lg bg-accent-red/10 text-sm text-accent-red break-all">{error}</div>}

      <div className="bg-surface-2 border border-surface-3 rounded-xl p-4 flex flex-wrap gap-6 text-sm text-muted">
        <span className="flex items-center gap-2 text-text"><FileText className="w-4 h-4" />{data.filename || '合同文件'}</span>
        <span>合同类型：{data.contract_type || '未识别'}</span>
        <span>风险评分：{data.risk_score}</span>
      </div>

      {data.risk_summary && <div className="bg-surface-2 border border-surface-3 rounded-xl p-4 text-sm">{data.risk_summary}</div>}

      <div className="bg-surface-2 border border-surface-3 rounded-xl overflow-hidden">
        <div className="flex border-b border-surface-3 overflow-x-auto">
          {tabs.map(item => (
            <button key={item.key} onClick={() => setTab(item.key)}
              className={`px-4 py-3 text-sm whitespace-nowrap border-b-2 ${tab === item.key ? 'text-accent-cyan border-accent-cyan' : 'text-muted border-transparent'}`}>
              {item.label}
            </button>
          ))}
        </div>
        <div className="p-4 space-y-3">
          {tab === 'clauses' && data.clauses.map(item => (
            <div key={item.id} className="p-3 bg-surface-1 border border-surface-3 rounded-lg">
              <div className="flex justify-between gap-3"><strong className="text-sm">{item.title}</strong><StatusBadge label={item.category} variant="info" /></div>
              <p className="text-sm text-muted mt-2 whitespace-pre-wrap">{item.content}</p>
            </div>
          ))}
          {tab === 'risks' && data.risk_findings.map((item, index) => (
            <div key={`${item.clause_id}-${index}`} className="p-3 bg-surface-1 border border-surface-3 rounded-lg">
              <div className="flex justify-between gap-3"><strong className="text-sm">{item.risk_type}</strong><StatusBadge label={RISK_MAP[item.risk_level]?.label || item.risk_level} variant={RISK_MAP[item.risk_level]?.variant || 'info'} /></div>
              <p className="text-sm text-muted mt-2">{item.description}</p>
              {item.rationale && <p className="text-xs text-muted mt-1">依据：{item.rationale}</p>}
            </div>
          ))}
          {tab === 'compliance' && (
            <>
              {data.missing_clauses.length > 0 && <div className="p-3 rounded-lg bg-accent-red/10 text-sm text-accent-red">缺失条款：{data.missing_clauses.join('、')}</div>}
              {data.compliance_findings.map((item, index) => (
                <div key={`${item.clause_id}-${index}`} className="p-3 bg-surface-1 border border-surface-3 rounded-lg">
                  <p className="text-sm">{item.issue}</p>
                  <p className="text-xs text-muted mt-1">法规：{item.regulation}</p>
                  {item.recommendation && <p className="text-xs text-muted mt-1">建议：{item.recommendation}</p>}
                </div>
              ))}
            </>
          )}
          {tab === 'suggestions' && data.suggestions.map((item, index) => (
            <div key={`${item.clause_id}-${index}`} className="p-3 bg-surface-1 border border-surface-3 rounded-lg">
              <div className="flex justify-between gap-3"><strong className="text-sm">{item.reason}</strong><StatusBadge label={item.priority} variant={item.priority === 'high' ? 'error' : 'warning'} /></div>
              {item.original_text && <p className="text-sm text-accent-red mt-2 line-through">{item.original_text}</p>}
              <p className="text-sm text-accent-green mt-1">{item.suggested_text}</p>
            </div>
          ))}
          {((tab === 'clauses' && !data.clauses.length) || (tab === 'risks' && !data.risk_findings.length) || (tab === 'compliance' && !data.compliance_findings.length) || (tab === 'suggestions' && !data.suggestions.length)) && (
            <p className="text-sm text-muted">暂无内容。</p>
          )}
        </div>
      </div>
    </div>
  )
}
