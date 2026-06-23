import { useState } from 'react'
import { useApi } from '../context/ApiContext'
import styles from './InboxTab.module.css'

const VERDICT_COLOR = {
  SCAM:      { bg:'var(--red-dim)',   border:'var(--red)',    color:'var(--red)' },
  SUSPECTED: { bg:'#2e1800',          border:'var(--yellow)', color:'var(--yellow)' },
  UNCERTAIN: { bg:'var(--bg4)',       border:'var(--border)', color:'var(--text2)' },
  SAFE:      { bg:'var(--green-dim)', border:'var(--green3)', color:'var(--green)' },
}

export default function InboxTab() {
  const { post } = useApi()
  const [host,  setHost]  = useState('imap.gmail.com')
  const [email, setEmail] = useState('')
  const [pass,  setPass]  = useState('')
  const [count, setCount] = useState(10)
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState(null)
  const [error,   setError]   = useState('')

  async function handleScan(e) {
    e.preventDefault()
    setError('')
    setResults(null)
    setLoading(true)
    try {
      const fd = new URLSearchParams({ imap_host: host, email_addr: email, password: pass, count })
      const data = await post('/email/scan-inbox', fd)
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.card}>
        <h2 className={styles.cardTitle}>📧 IMAP Inbox Scanner</h2>
        <p className={styles.cardSub}>
          Connect your inbox and scan recent emails for phishing, SPF/DKIM/DMARC failures, and header spoofing.
        </p>
        <form onSubmit={handleScan} className={styles.form}>
          <Field label="IMAP Host">
            <input value={host} onChange={e => setHost(e.target.value)} placeholder="imap.gmail.com" required />
          </Field>
          <div className={styles.row2}>
            <Field label="Email Address">
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@gmail.com" required />
            </Field>
            <Field label="App Password">
              <input type="password" value={pass} onChange={e => setPass(e.target.value)} placeholder="App password" required />
            </Field>
          </div>
          <Field label={`Emails to scan: ${count}`}>
            <input type="range" min={1} max={50} value={count} onChange={e => setCount(Number(e.target.value))} className={styles.range} />
          </Field>
          {error && <div className={styles.error}>⚠ {error}</div>}
          <button className={styles.scanBtn} type="submit" disabled={loading}>
            {loading ? '⏳ Connecting...' : '📬 Scan Inbox'}
          </button>
        </form>
      </div>

      {results && (
        <div className={styles.results}>
          <div className={styles.summary}>Scanned {results.emails_scanned} email(s)</div>
          {(results.results ?? []).map((em, i) => {
            if (em.error) return <div key={i} className={styles.errCard}>{em.error}</div>
            const a = em.analysis ?? {}
            const verdict = a.verdict ?? 'UNCERTAIN'
            const vc = VERDICT_COLOR[verdict] ?? VERDICT_COLOR.UNCERTAIN
            const score = Math.round(a.score ?? 0)
            return (
              <div key={i} className={styles.emailCard}>
                <div className={styles.emailMeta}>
                  <div className={styles.from}>{em.from || '(unknown)'}</div>
                  <div className={styles.subject}>{em.subject || '(no subject)'}</div>
                  <div className={styles.date}>{em.date || ''}</div>
                </div>
                <div
                  className={styles.scoreBadge}
                  style={{ background: vc.bg, border: `1px solid ${vc.border}`, color: vc.color }}
                >
                  {score} — {verdict}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div className={{ display:'flex', flexDirection:'column', gap:'0.4rem' }}>
      <label style={{ fontSize:'0.72rem', color:'var(--text2)', textTransform:'uppercase', letterSpacing:'0.08em' }}>
        {label}
      </label>
      {children}
    </div>
  )
}
