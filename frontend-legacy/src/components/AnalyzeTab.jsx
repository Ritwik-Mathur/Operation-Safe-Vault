import { useState, useRef } from 'react'
import { useApi } from '../context/ApiContext'
import ScoreRing from './ScoreRing'
import ResultPanel from './ResultPanel'
import styles from './AnalyzeTab.module.css'

const INPUTS = [
  { id: 'text',  icon: '💬', label: 'Text / SMS' },
  { id: 'url',   icon: '🔗', label: 'URL' },
  { id: 'voice', icon: '🎙', label: 'Voice' },
  { id: 'file',  icon: '📎', label: 'File' },
  { id: 'email', icon: '✉',  label: 'Email' },
]

export default function AnalyzeTab() {
  const { post } = useApi()
  const [activeInput, setActiveInput] = useState('text')
  const [loading, setLoading]         = useState(false)
  const [loadingText, setLoadingText] = useState('Scanning...')
  const [result, setResult]           = useState(null)
  const [lastInput, setLastInput]     = useState('')
  const [error, setError]             = useState('')

  // form field refs / state
  const [textMsg, setTextMsg]       = useState('')
  const [sender, setSender]         = useState('')
  const [channel, setChannel]       = useState('sms')
  const [urlVal, setUrlVal]         = useState('')
  const [audioFile, setAudioFile]   = useState(null)
  const [attachFile, setAttachFile] = useState(null)
  const [rawEmail, setRawEmail]     = useState('')
  const [emailBody, setEmailBody]   = useState('')
  const [emailSender, setEmailSender] = useState('')

  const LOADING_MSGS = {
    text:  'Analyzing message...',
    url:   'Sandboxing URL — this may take ~10s...',
    voice: 'Processing audio...',
    file:  'Running YARA + AV scan...',
    email: 'Checking headers + SPF/DKIM/DMARC...',
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    setLoadingText(LOADING_MSGS[activeInput])

    try {
      let data
      const fd = new FormData()

      if (activeInput === 'text') {
        fd.append('message', textMsg)
        fd.append('sender', sender || 'unknown')
        fd.append('channel', channel)
        setLastInput(textMsg)
        data = await post('/analyze/text', fd)

      } else if (activeInput === 'url') {
        fd.append('url', urlVal)
        setLastInput(urlVal)
        data = await post('/analyze/url', fd)

      } else if (activeInput === 'voice') {
        if (!audioFile) { setError('Please select an audio file.'); return }
        fd.append('audio', audioFile)
        setLastInput(audioFile.name)
        data = await post('/analyze/voice', fd)

      } else if (activeInput === 'file') {
        if (!attachFile) { setError('Please select a file.'); return }
        fd.append('attachment', attachFile)
        setLastInput(attachFile.name)
        data = await post('/analyze/file', fd)

      } else if (activeInput === 'email') {
        fd.append('raw_email', rawEmail)
        fd.append('body', emailBody)
        fd.append('sender', emailSender || 'unknown')
        setLastInput(rawEmail || emailBody)
        data = await post('/analyze/email', fd)
      }

      setResult(data)
    } catch (err) {
      setError(err.message || 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  function switchInput(id) {
    setActiveInput(id)
    setResult(null)
    setError('')
  }

  return (
    <div className={styles.wrap}>
      {/* Input type selector */}
      <div className={styles.selector}>
        {INPUTS.map(inp => (
          <button
            key={inp.id}
            className={`${styles.selBtn} ${activeInput === inp.id ? styles.selActive : ''}`}
            onClick={() => switchInput(inp.id)}
          >
            <span>{inp.icon}</span> {inp.label}
          </button>
        ))}
      </div>

      {/* Form card */}
      <div className={styles.card}>
        <form onSubmit={handleSubmit} className={styles.form}>

          {activeInput === 'text' && (
            <>
              <Field label="Message / SMS">
                <textarea
                  rows={4}
                  placeholder="Paste suspicious SMS, WhatsApp message, or email body..."
                  value={textMsg}
                  onChange={e => setTextMsg(e.target.value)}
                  required
                />
              </Field>
              <div className={styles.row2}>
                <Field label="Sender">
                  <input value={sender} onChange={e => setSender(e.target.value)} placeholder="+91-XXXXXXXXXX or unknown" />
                </Field>
                <Field label="Channel">
                  <select value={channel} onChange={e => setChannel(e.target.value)}>
                    <option value="sms">SMS</option>
                    <option value="email">Email</option>
                    <option value="whatsapp">WhatsApp</option>
                  </select>
                </Field>
              </div>
            </>
          )}

          {activeInput === 'url' && (
            <Field label="Suspicious URL">
              <input
                type="text"
                placeholder="https://suspicious-link.com/verify?otp=..."
                value={urlVal}
                onChange={e => setUrlVal(e.target.value)}
                required
              />
              <p className={styles.hint}>SSL + WHOIS + Playwright behavioral sandbox</p>
            </Field>
          )}

          {activeInput === 'voice' && (
            <Field label="Audio File">
              <FileDrop
                accept="audio/*"
                file={audioFile}
                onFile={setAudioFile}
                icon="🎙"
                hint="Supports .wav .mp3 .ogg .m4a — Acoustic + STT + Deepfake detection"
              />
            </Field>
          )}

          {activeInput === 'file' && (
            <Field label="Attachment">
              <FileDrop
                accept="*/*"
                file={attachFile}
                onFile={setAttachFile}
                icon="📎"
                hint="Any file type — YARA rules + ClamAV + VirusTotal scan"
              />
            </Field>
          )}

          {activeInput === 'email' && (
            <>
              <Field label="Raw Email (paste full RFC822 with headers)">
                <textarea
                  rows={5}
                  placeholder="Paste full raw email: From:, Received:, DKIM-Signature:, body..."
                  value={rawEmail}
                  onChange={e => setRawEmail(e.target.value)}
                />
              </Field>
              <div className={styles.divider}>— OR just the body —</div>
              <Field label="Email Body">
                <textarea rows={3} placeholder="Just the message body..." value={emailBody} onChange={e => setEmailBody(e.target.value)} />
              </Field>
              <Field label="Sender Email">
                <input placeholder="sender@domain.com" value={emailSender} onChange={e => setEmailSender(e.target.value)} />
              </Field>
            </>
          )}

          {error && <div className={styles.errorMsg}>⚠ {error}</div>}

          <button className={styles.scanBtn} type="submit" disabled={loading}>
            {loading ? <><span className={styles.spinnerInline} /> {loadingText}</> : '⚡ Scan Now'}
          </button>
        </form>
      </div>

      {/* Result */}
      {result && (
        <ResultPanel result={result} lastInput={lastInput} />
      )}
    </div>
  )
}

/* ── Field wrapper ── */
function Field({ label, children }) {
  return (
    <div style={{ display:'flex', flexDirection:'column', gap:'0.4rem' }}>
      <label style={{ fontSize:'0.72rem', color:'var(--text2)', textTransform:'uppercase', letterSpacing:'0.08em' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

/* ── File Drop ── */
function FileDrop({ accept, file, onFile, icon, hint }) {
  const inputRef = useRef()
  const [dragging, setDragging] = useState(false)

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }

  return (
    <div
      className={`${styles.fileDrop} ${dragging ? styles.fileDropOver : ''}`}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current.click()}
    >
      <span className={styles.fileIcon}>{icon}</span>
      {file
        ? <p className={styles.fileName}>{file.name}</p>
        : <><p>Drop file here or <u>browse</u></p><p className={styles.fileHint}>{hint}</p></>
      }
      <input ref={inputRef} type="file" accept={accept} style={{ display:'none' }} onChange={e => onFile(e.target.files[0])} />
    </div>
  )
}
