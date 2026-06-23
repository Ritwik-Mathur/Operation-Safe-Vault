import styles from './Topbar.module.css'

export default function Topbar({ title }) {
  return (
    <header className={styles.topbar}>
      <div className={styles.title}>{title}</div>
      <div className={styles.badge}>● LIVE</div>
    </header>
  )
}
