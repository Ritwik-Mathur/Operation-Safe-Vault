"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Search, AlertCircle, CheckCircle, ShieldAlert, Loader2, Copy } from 'lucide-react';

// All requests go through NEXT_PUBLIC_API_URL (falls back to localhost:8000)
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

// ── Types ────────────────────────────────────────────────────────────────────
interface ScanResult {
  score: number;
  verdict: string;
  reasons: string[];
  analysis_id?: string;
  mode: 'text' | 'url';
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function looksLikeUrl(s: string) {
  return /^https?:\/\//i.test(s.trim()) || /^www\./i.test(s.trim());
}

async function callTextEndpoint(message: string): Promise<ScanResult> {
  const fd = new FormData();
  fd.append('message', message);
  fd.append('sender', 'unknown');
  fd.append('channel', 'sms');

  const res = await fetch(`${API_BASE}/analyze/text`, { method: 'POST', body: fd });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Backend returned ${res.status}${body ? ': ' + body.slice(0, 120) : ''}`);
  }
  const data = await res.json();
  // /analyze/text → { combined: { score, verdict, reasons }, analysis_id, ... }
  const combined = data.combined ?? data;
  return {
    score:       Math.round(combined.score ?? 0),
    verdict:     combined.verdict ?? 'UNKNOWN',
    reasons:     combined.reasons ?? [],
    analysis_id: data.analysis_id,
    mode:        'text',
  };
}

async function callUrlEndpoint(url: string): Promise<ScanResult> {
  const fd = new FormData();
  // normalise: add https:// if missing
  const normalized = /^https?:\/\//i.test(url) ? url : `https://${url}`;
  fd.append('url', normalized);

  const res = await fetch(`${API_BASE}/analyze/url`, { method: 'POST', body: fd });
  if (!res.ok) {
    const body = await res.text().catch(() => '');
    throw new Error(`Backend returned ${res.status}${body ? ': ' + body.slice(0, 120) : ''}`);
  }
  const data = await res.json();
  return {
    score:       Math.round(data.score ?? 0),
    verdict:     data.verdict ?? 'UNKNOWN',
    reasons:     data.reasons ?? [],
    analysis_id: data.analysis_id,
    mode:        'url',
  };
}

// ── Component ────────────────────────────────────────────────────────────────
export const ThreatSandbox = () => {
  const [input, setInput]     = useState('');
  const [status, setStatus]   = useState<'idle' | 'scanning' | 'complete' | 'error'>('idle');
  const [result, setResult]   = useState<ScanResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied]   = useState(false);

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    setStatus('scanning');
    setResult(null);
    setErrorMsg(null);

    try {
      const scanResult = looksLikeUrl(trimmed)
        ? await callUrlEndpoint(trimmed)
        : await callTextEndpoint(trimmed);

      setResult(scanResult);
      setStatus('complete');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Request failed';
      setErrorMsg(
        msg.includes('Failed to fetch') || msg.includes('NetworkError')
          ? 'Cannot reach backend — make sure it is running on port 8000.'
          : msg,
      );
      setStatus('error');
    }
  };

  const handleReset = () => {
    setStatus('idle');
    setResult(null);
    setErrorMsg(null);
    setInput('');
  };

  const handleBlock = async () => {
    // "Block Source" submits negative feedback to /feedback so the input
    // gets added to the scam vector DB for future matching.
    if (!result) return;
    try {
      const fd = new FormData();
      fd.append('analysis_id', result.analysis_id ?? 'sandbox');
      fd.append('user_verdict', 'scam');
      fd.append('original_score', String(result.score));
      fd.append('original_verdict', result.verdict);
      fd.append('source', result.mode);
      fd.append('original_input', input);
      fd.append('comment', 'Blocked from Threat Sandbox');
      await fetch(`${API_BASE}/feedback`, { method: 'POST', body: fd });
    } catch {
      // non-critical; don't block the UI
    }
    handleReset();
  };

  const handleCopyId = () => {
    if (!result?.analysis_id) return;
    navigator.clipboard.writeText(result.analysis_id).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  // Colour helpers
  const isHigh  = (result?.score ?? 0) > 50;
  const colour  = isHigh ? 'text-error' : 'text-primary';
  const ring    = isHigh ? 'stroke-error' : 'stroke-primary';
  const border  = isHigh ? 'bg-error/5 border-error' : 'bg-primary/5 border-primary';

  return (
    <section className="py-24 px-6 bg-surface-container-lowest">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-16 space-y-4">
          <h2 className="text-primary font-headline font-bold uppercase tracking-[0.3em] text-sm">Interactive Demo</h2>
          <h3 className="text-4xl md:text-5xl font-headline font-bold text-white tracking-tight">
            Challenge the <span className="text-primary italic">Sovereign</span>.
          </h3>
          <p className="text-on-surface-variant font-light text-lg">
            Paste any URL or text snippet — auto-detected, sent to the live backend, real result in seconds.
          </p>
        </div>

        <div className="glass-panel p-8 md:p-12 rounded-[2.5rem] border border-primary/20 shadow-[0_0_80px_rgba(49,227,104,0.05)] relative overflow-hidden bg-black/40">
          {/* ── Input form ─────────────────────────────────────────────── */}
          <form onSubmit={handleScan} className="relative z-10 flex flex-col md:flex-row gap-4 mb-12">
            <div className="relative flex-1 group">
              <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none">
                <Search className="w-5 h-5 text-on-surface-variant/40 group-focus-within:text-primary transition-colors" />
              </div>
              <input
                id="sandbox-input"
                type="text"
                placeholder="Paste URL, SMS, or message snippet — auto-detected…"
                className="w-full bg-background/50 border border-outline/20 rounded-2xl py-5 pl-12 pr-6 text-white focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all font-light"
                value={input}
                onChange={(e) => setInput(e.target.value)}
              />
            </div>
            <motion.button
              id="sandbox-scan-btn"
              type="submit"
              disabled={status === 'scanning' || !input.trim()}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="bg-primary text-black font-headline font-bold px-10 py-5 rounded-2xl shadow-lg shadow-primary/20 hover:bg-primary-dark transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              {status === 'scanning' ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  ANALYZING
                </>
              ) : (
                <>
                  INITIATE SCAN
                  <Shield className="w-5 h-5" />
                </>
              )}
            </motion.button>
          </form>

          <AnimatePresence mode="wait">

            {/* ── Scanning ──────────────────────────────────────────────── */}
            {status === 'scanning' && (
              <motion.div
                key="scanning"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center py-12 space-y-6"
              >
                <div className="relative h-32 w-32">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-0 border-4 border-primary/20 border-t-primary rounded-full shadow-[0_0_20px_rgba(49,227,104,0.3)]"
                  />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <Shield className="w-12 h-12 text-primary animate-pulse" />
                  </div>
                </div>
                <div className="text-center space-y-2">
                  <p className="text-primary font-headline font-bold tracking-widest text-xs">NEURAL ANALYSIS IN PROGRESS</p>
                  <div className="flex gap-1 justify-center">
                    {["Deepfake Check", "URL Detonation", "Metadata Forensic", "Pattern Match"].map((step, i) => (
                      <motion.div
                        key={i}
                        animate={{ opacity: [0.3, 1, 0.3] }}
                        transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
                        className="text-[10px] text-on-surface-variant bg-surface px-2 py-1 rounded border border-outline/10 uppercase"
                      >
                        {step}
                      </motion.div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* ── Error ─────────────────────────────────────────────────── */}
            {status === 'error' && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-col items-center py-12 space-y-4"
              >
                <AlertCircle className="w-12 h-12 text-error" />
                <p className="text-error font-headline font-bold">Analysis Failed</p>
                <p className="text-on-surface-variant text-sm text-center max-w-sm">{errorMsg}</p>
                <button
                  onClick={handleReset}
                  className="border border-outline/20 bg-surface/50 text-white font-headline text-xs font-bold py-3 px-8 rounded-xl hover:bg-surface transition-colors"
                >
                  TRY AGAIN
                </button>
              </motion.div>
            )}

            {/* ── Result ────────────────────────────────────────────────── */}
            {status === 'complete' && result && (
              <motion.div
                key="complete"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="grid md:grid-cols-2 gap-12 items-center py-4"
              >
                {/* Score dial */}
                <div className="flex justify-center">
                  <div className="relative h-64 w-64 flex items-center justify-center">
                    <svg className="w-full h-full -rotate-90">
                      <circle cx="128" cy="128" r="110" className="stroke-surface-high fill-none" strokeWidth="12" />
                      <motion.circle
                        initial={{ strokeDasharray: "0, 1000" }}
                        animate={{ strokeDasharray: `${(result.score / 100) * 690}, 1000` }}
                        transition={{ duration: 1.5, ease: "easeOut" }}
                        cx="128" cy="128" r="110"
                        className={`fill-none ${ring}`}
                        strokeWidth="12"
                        strokeLinecap="round"
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center space-y-1">
                      <span className={`text-6xl font-headline font-bold ${colour} glow-text`}>{result.score}</span>
                      <span className="text-[10px] font-headline text-on-surface-variant font-bold tracking-widest uppercase">THREAT SCORE</span>
                      {result.analysis_id && (
                        <button
                          onClick={handleCopyId}
                          className="flex items-center gap-1 text-[8px] text-on-surface-variant/40 hover:text-on-surface-variant transition-colors mt-1"
                          title="Copy analysis ID"
                        >
                          <Copy className="w-2.5 h-2.5" />
                          {copied ? 'Copied!' : `ID: ${result.analysis_id}`}
                        </button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Verdict card + reasons + actions */}
                <div className="space-y-6">
                  <div className={`p-6 rounded-2xl border-l-[6px] ${border} shadow-xl`}>
                    <div className="flex items-center gap-3 mb-3">
                      {isHigh ? (
                        <ShieldAlert className="w-6 h-6 text-error" />
                      ) : (
                        <ShieldCheck className="w-6 h-6 text-primary" />
                      )}
                      <h4 className="text-2xl font-headline font-bold text-white tracking-tight">
                        {result.verdict}
                      </h4>
                    </div>
                    <p className="text-on-surface-variant text-sm font-light leading-relaxed mb-4">
                      {isHigh
                        ? 'High-confidence threat detected. Review reasons below before taking action.'
                        : 'No significant malicious patterns identified. Result is based on live analysis.'}
                    </p>

                    {/* Reasons list */}
                    {result.reasons.length > 0 && (
                      <ul className="space-y-1 max-h-28 overflow-y-auto pr-1">
                        {result.reasons.slice(0, 6).map((r, i) => (
                          <li key={i} className="text-[10px] text-on-surface-variant font-light leading-relaxed flex gap-1.5">
                            <span className="text-primary/60 shrink-0">•</span>
                            {r}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="flex gap-4">
                    <button
                      id="sandbox-reset-btn"
                      className="flex-1 border border-outline/20 bg-surface/50 text-white font-headline text-xs font-bold py-4 rounded-xl hover:bg-surface transition-colors"
                      onClick={handleReset}
                    >
                      RESET SCANNER
                    </button>
                    <button
                      id="sandbox-action-btn"
                      onClick={isHigh ? handleBlock : handleReset}
                      className={`flex-1 ${isHigh ? 'bg-error text-black' : 'bg-primary text-black'} font-headline text-xs font-bold py-4 rounded-xl shadow-lg transition-all`}
                    >
                      {isHigh ? 'BLOCK SOURCE' : 'VERIFY IDENTITY'}
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {/* ── Idle ──────────────────────────────────────────────────── */}
            {status === 'idle' && (
              <motion.div
                key="idle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-outline/10 rounded-3xl"
              >
                <AlertCircle className="w-12 h-12 text-on-surface-variant/20 mb-4" />
                <p className="text-on-surface-variant/40 font-light text-sm">
                  URLs are analysed with the URL Sandbox. Everything else uses Text + Credential detection.
                </p>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </section>
  );
};

// ── Local icon shim (was inline in original) ──────────────────────────────────
const ShieldCheck = ({ className }: { className: string }) => (
  <CheckCircle className={className} />
);
