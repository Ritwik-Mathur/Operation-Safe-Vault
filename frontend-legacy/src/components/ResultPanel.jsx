import { useState } from 'react'
import { useApi } from '../context/ApiContext'
import ScoreRing from './ScoreRing'
import styles from './ResultPanel.module.css'

const VERDICT_STYLE = {
  SCAM:      { bg: 'var(--red-dim)',    border: 'var(--red)',    color: 'var(--red)' },
  SUSPECTED: { bg: '#2e1800',           border: 'var(--yellow)', color: 'var(--yellow)' },
  UNCERTAIN: { bg: 'var(--bg4)',        border: 'var(--border)', color: 'var(--text2)' },
  SAFE:      { bg: 'var(--green-dim)', border: 'var(--green3)', color: 'var(--green)' },
}

function barColor(score) {
  if (score >= 70) return 'var(--red)'
  if (score >= 40) return 'var(--yellow)'
  return 'var(--green)'
}

export default function ResultPanel({ result, lastInput }) {
  const { post } = useApi()
  const [fbDone, setFbDone] = useState(false)

  const combined    = result.combined || result
  const components  = result.components || {}
  const analysisId  = result.analysis_id || ''

  const score   = Math.round(combined.score   ?? 0)
  const verdict = combined.verdict  ?? 'UNCERTAIN'
  const vs      = VERDICT_STYLE[verdict] || VERDICT_STYLE.UNCERTAIN

  async function submitFeedback(userVerdict) {
    try {
      const fd = new URLSearchParams({
        analysis_id:      analysisId,
        user_verdict:     userVerdict,
        original_score:   combined.score  ?? 0,
        original_verdict: verdict,
        original_input:   lastInput ?? '',
      })
      await post('/feedback', fd)
      setFbDone(true)
    } catch {}
  }

  return (
    <div className={styles.panel}>

      {/* Score + meta row */}
      <div className={styles.scoreRow}>
        <ScoreRing score={score} />
        <div className={styles.meta}>
          <div
            className={styles.verdictBadge}
            style={{ background: vs.bg, border: `1px solid ${vs.border}`, color: vs.color }}
          >
            {verdict}
          </div>
          <MetaRow k="Severity"   v={combined.severity   ?? '--'} />
          <MetaRow k="Confidence" v={combined.confidence ?? '--'} />
          <MetaRow k="Fidelity"   v={combined.fidelity   ?? '--'} />
          <MetaRow k="Detectors"  v={(combined.detectors_used ?? []).join(', ') || '--'} />
          <MetaRow k="ID"         v={analysisId || '--'} mono />
        </div>
      </div>

      {/* Detection signals */}
      <Section title="⚠ Detection Signals">
        {(combined.reasons ?? []).length === 0
          ? <p className={styles.noSignals}>No specific signals detected.</p>
          : <ul className={styles.reasons}>
              {combined.reasons.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
        }
      </Section>

      {/* Component bars */}
      {Object.keys(components).length > 0 && (
        <Section title="📡 Component Breakdown">
          <div className={styles.bars}>
            {Object.entries(components).map(([k, c]) => {
              if (!c || c.score === undefined) return null
              const s = Math.round(c.score)
              return (
                <div key={k} className={styles.barRow}>
                  <div className={styles.barLabel}>{k}</div>
                  <div className={styles.barTrack}>
                    <div
                      className={styles.barFill}
                      style={{ width: `${s}%`, background: barColor(s) }}
                    />
                  </div>
                  <div className={styles.barScore}>{s}</div>
                  <div className={styles.barVerdict} style={{ color: VERDICT_STYLE[c.verdict]?.color ?? 'var(--text2)' }}>
                    {c.verdict ?? ''}
                  </div>
                </div>
              )
            })}
          </div>
        </Section>
      )}

      {/* Feedback */}
      <Section title="Was this correct?">
        {fbDone
          ? <div className={styles.fbAck}>✓ Feedback recorded — thank you!</div>
          : <div className={styles.fbBtns}>
              <FbBtn label="🚨 Confirm Scam" cls={styles.fbScam}  onClick={() => submitFeedback('scam')} />
              <FbBtn label="✅ Mark Safe"    cls={styles.fbSafe}  onClick={() => submitFeedback('safe')} />
              <FbBtn label="🤔 Unsure"       cls={styles.fbUnsure} onClick={() => submitFeedback('unsure')} />
            </div>
        }
      </Section>

    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className={styles.section}>
      <div className={styles.sectionTitle}>{title}</div>
      {children}
    </div>
  )
}

function MetaRow({ k, v, mono }) {
  return (
    <div className={styles.metaRow}>
      <span className={styles.metaKey}>{k}</span>
      <span className={`${styles.metaVal} ${mono ? styles.mono : ''}`}>{v}</span>
    </div>
  )
}

function FbBtn({ label, cls, onClick }) {
  return <button className={`${styles.fbBtn} ${cls}`} onClick={onClick}>{label}</button>
}
