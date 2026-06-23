import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import AnalyzeTab from './components/AnalyzeTab'
import InboxTab from './components/InboxTab'
import FeedbackTab from './components/FeedbackTab'
import { ApiProvider } from './context/ApiContext'
import './App.css'

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze')

  const titles = {
    analyze: 'Threat Analyzer',
    inbox: 'Inbox Scanner',
    feedback: 'Feedback & Stats',
  }

  return (
    <ApiProvider>
      <div className="layout">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <div className="content-area">
          <Topbar title={titles[activeTab]} />
          <main className="main-scroll">
            {activeTab === 'analyze'  && <AnalyzeTab />}
            {activeTab === 'inbox'    && <InboxTab />}
            {activeTab === 'feedback' && <FeedbackTab />}
          </main>
        </div>
      </div>
    </ApiProvider>
  )
}
