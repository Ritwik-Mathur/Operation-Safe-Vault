import { useState, useEffect } from 'react'
import { useApi } from '../context/ApiContext'
import styles from './FeedbackTab.module.css'

export default function FeedbackTab() {
  const { get } = useApi()
  const [stats,  setStats]  = useState(null)
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const [s, r] = await Promise.all([
        get('/feedback/stats'),
        get('/feedback/recent?limit=30'),
      ])
      setStats(s)
      setRecent(Array.isArray(r) ? r : (r.entries ?? []))
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const VERDICT_COLOR = {
    scam:      'var(--red)',
    safe:      'var(--green)',
    unsure:    'var(--yellow)',
    SCAM:      'var(--red)',
    SUSPECTED: 'var(--yellow)',
    UNCERTAIN: 'var(--text2)',
    SAFE:      'var(--green)',
  }

  return (
    <div className={styles.wrap}>
      {/* Stats cards */}
      <div className={styles.statsGrid}>
        <StatCard label="Total Feedback"   value={stats?.total_feedback   ?? '--'} />
        <StatCard label="System Accuracy"  value={stats?.accuracy_pct !== undefined ? `${Math.round(stats.accuracy_pct)}%` : '--%'} green />
        <StatCard label="Confirmed Scams"  value={stats?.confirmed_scams  ?? '--'} />
        <StatCard label="False Positives"  value={stats?.false_positives  ?? '--'} />
      </div>

      {/* Recent table */}
      <div className={styles.tableSection}>
        <div className={styles.tableHeader}>
          <span className={styles.sectionTitle}>Recent Feedback</span>
          <button className={styles.refreshBtn} onClick={load} disabled={loading}>
            {loading ? '...' : '↻ Refresh'}
          </button>
        </div>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>ID</th>
                <th>System Verdict</th>
                <th>User Verdict</th>
                <th>Score</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {recent.length === 0
                ? <tr><td colSpan={5} className={styles.empty}>No feedback submitted yet.</td></tr>
                : recent.map((e, i) => (
                    <tr key={i}>
                      <td className={styles.mono}>{e.analysis_id || '--'}</td>
                      <td style={{ color: VERDICT_COLOR[e.original_verdict] ?? 'var(--text)' }}>
                        {e.original_verdict || '--'}
                      </td>
                      <td style={{ color: VERDICT_COLOR[e.user_verdict] ?? 'var(--text)' }}>
                        {e.user_verdict || '--'}
                      </td>
                      <td>{e.original_score !== undefined ? Math.round(e.original_score) : '--'}</td>
                      <td className={styles.dim}>{e.source || '--'}</td>
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function StatCard({ label, value, green }) {
  return (
    <div className={styles.statCard}>
      <div className={`${styles.statNum} ${green ? styles.statGreen : ''}`}>{value}</div>
      <div className={styles.statLabel}>{label}</div>
    </div>
  )
}
