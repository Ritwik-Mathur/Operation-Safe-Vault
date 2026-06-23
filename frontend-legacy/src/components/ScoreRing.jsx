import { useEffect, useRef } from 'react'
import styles from './ScoreRing.module.css'

const CIRC = 2 * Math.PI * 52  // ≈ 326.7

function scoreColor(score) {
  if (score >= 70) return 'var(--red)'
  if (score >= 40) return 'var(--yellow)'
  return 'var(--green)'
}

export default function ScoreRing({ score }) {
  const fillRef = useRef()

  useEffect(() => {
    const offset = CIRC - (score / 100) * CIRC
    if (fillRef.current) {
      fillRef.current.style.strokeDashoffset = offset
      fillRef.current.style.stroke = scoreColor(score)
    }
  }, [score])

  return (
    <div className={styles.wrap}>
      <svg className={styles.svg} viewBox="0 0 120 120">
        <circle className={styles.bg}   cx="60" cy="60" r="52" />
        <circle className={styles.fill} cx="60" cy="60" r="52" ref={fillRef}
          style={{ strokeDasharray: CIRC, strokeDashoffset: CIRC }} />
      </svg>
      <div className={styles.center}>
        <div className={styles.number} style={{ color: scoreColor(score) }}>{Math.round(score)}</div>
        <div className={styles.sub}>/ 100</div>
      </div>
    </div>
  )
}
