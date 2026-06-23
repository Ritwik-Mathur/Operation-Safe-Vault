import { useApi } from '../context/ApiContext'
import styles from './Sidebar.module.css'

const TABS = [
  { id: 'analyze',  icon: '⚡', label: 'Analyze' },
  { id: 'inbox',    icon: '📧', label: 'Inbox Scan' },
  { id: 'feedback', icon: '📊', label: 'Feedback' },
]

export default function Sidebar({ activeTab, setActiveTab }) {
  const { online } = useApi()

  return (
    <aside className={styles.sidebar}>
      <div className={styles.logo}>
        <span className={styles.logoIcon}>🛡</span>
        <div>
          <div className={styles.logoText}>FRAUD</div>
          <div className={styles.logoAccent}>SHIELD AI</div>
        </div>
      </div>

      <nav className={styles.nav}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`${styles.navBtn} ${activeTab === t.id ? styles.active : ''}`}
            onClick={() => setActiveTab(t.id)}
          >
            <span className={styles.navIcon}>{t.icon}</span>
            <span className={styles.navLabel}>{t.label}</span>
          </button>
        ))}
      </nav>

      <div className={styles.footer}>
        <span className={`${styles.dot} ${online ? styles.dotOnline : ''}`} />
        <span className={styles.footerText}>{online ? 'API Online' : 'API Offline'}</span>
      </div>
    </aside>
  )
}
