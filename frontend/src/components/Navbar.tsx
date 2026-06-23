"use client";

import React, { useState, useEffect } from 'react';
import { Shield, Menu, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Inline Quick-Analyze Modal ────────────────────────────────────────────────
// Clicking "Analyze Threat" opens a small overlay where you can type text/URL
// and hit the appropriate backend endpoint without leaving the page.

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

type Mode = 'text' | 'url';

interface QuickResult {
  score: number;
  verdict: string;
  reasons: string[];
}

function QuickAnalyzeModal({ onClose }: { onClose: () => void }) {
  const [mode, setMode] = useState<Mode>('text');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QuickResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const analyze = async () => {
    if (!input.trim()) return;
    setLoading(true);
    setResult(null);
    setError(null);

    try {
      const fd = new FormData();

      if (mode === 'text') {
        fd.append('message', input);
        fd.append('sender', 'unknown');
        fd.append('channel', 'sms');
        const res = await fetch(`${API_BASE}/analyze/text`, { method: 'POST', body: fd });
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        const data = await res.json();
        // /analyze/text returns { combined: { score, verdict, reasons }, ... }
        const combined = data.combined ?? data;
        setResult({
          score:   Math.round(combined.score ?? 0),
          verdict: combined.verdict ?? 'UNKNOWN',
          reasons: combined.reasons ?? [],
        });
      } else {
        fd.append('url', input);
        const res = await fetch(`${API_BASE}/analyze/url`, { method: 'POST', body: fd });
        if (!res.ok) throw new Error(`Server error ${res.status}`);
        const data = await res.json();
        setResult({
          score:   Math.round(data.score ?? 0),
          verdict: data.verdict ?? 'UNKNOWN',
          reasons: data.reasons ?? [],
        });
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Request failed — is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (s: number) =>
    s >= 70 ? 'text-red-400' : s >= 45 ? 'text-orange-400' : 'text-primary';

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.92, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.92, opacity: 0 }}
        className="glass-panel rounded-2xl border border-outline/20 bg-black/60 p-6 w-full max-w-lg shadow-2xl"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            <span className="font-headline font-bold text-white text-sm uppercase tracking-widest">
              Quick Threat Analysis
            </span>
          </div>
          <button onClick={onClose} className="text-on-surface-variant/50 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode toggle */}
        <div className="flex gap-2 mb-4">
          {(['text', 'url'] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setResult(null); setError(null); }}
              className={`px-4 py-1.5 rounded-lg text-xs font-headline font-bold uppercase tracking-widest transition-all ${
                mode === m
                  ? 'bg-primary text-black'
                  : 'border border-outline/20 text-on-surface-variant hover:border-primary/30'
              }`}
            >
              {m === 'text' ? 'Text / SMS' : 'URL'}
            </button>
          ))}
        </div>

        {/* Input */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            mode === 'text'
              ? 'Paste SMS, message, or email body…'
              : 'https://suspicious-link.example.com'
          }
          rows={3}
          className="w-full bg-background/50 border border-outline/20 rounded-xl p-3 text-white text-sm focus:outline-none focus:border-primary/50 resize-none font-light mb-3"
        />

        {/* Submit */}
        <button
          id="quick-analyze-submit"
          disabled={loading || !input.trim()}
          onClick={analyze}
          className="w-full bg-primary text-black font-headline font-bold py-3 rounded-xl text-sm shadow-lg shadow-primary/20 hover:bg-primary-dark transition-all disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
              Analyzing…
            </>
          ) : (
            `Analyze ${mode === 'text' ? 'Text' : 'URL'}`
          )}
        </button>

        {/* Error */}
        {error && (
          <p className="mt-3 text-xs text-red-400 text-center">{error}</p>
        )}

        {/* Result */}
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mt-4 p-4 rounded-xl border-l-4 ${
              result.score >= 70 ? 'border-red-400 bg-red-400/5' :
              result.score >= 45 ? 'border-orange-400 bg-orange-400/5' :
              'border-primary bg-primary/5'
            }`}
          >
            <div className="flex items-center gap-3 mb-2">
              <span className={`text-3xl font-headline font-bold ${scoreColor(result.score)}`}>
                {result.score}
              </span>
              <div>
                <p className={`font-headline font-bold text-sm ${scoreColor(result.score)}`}>
                  {result.verdict}
                </p>
                <p className="text-[10px] text-on-surface-variant">Threat Score / 100</p>
              </div>
            </div>
            {result.reasons.slice(0, 4).map((r, i) => (
              <p key={i} className="text-[10px] text-on-surface-variant font-light leading-relaxed">
                • {r}
              </p>
            ))}
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}

// ── Navbar ─────────────────────────────────────────────────────────────────────
export const Navbar = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => setIsScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${isScrolled ? 'bg-background/80 backdrop-blur-xl py-4 shadow-2xl shadow-black/50' : 'bg-transparent py-6'}`}>
        <div className="max-w-7xl mx-auto px-6 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Shield className="text-primary w-8 h-8 drop-shadow-[0_0_8px_rgba(49,227,104,0.4)]" />
            <span className="text-xl font-bold tracking-tighter text-on-background font-headline">
              FRAUD SHIELD <span className="text-primary">AI</span>
            </span>
          </div>

          <div className="hidden md:flex items-center gap-10">
            {[['Product', '#product'], ['Tech Stack', '#tech-stack'], ['Impact', '#impact']].map(([label, href]) => (
              <a
                key={label}
                href={href}
                className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors font-headline tracking-tight"
              >
                {label}
              </a>
            ))}
            <a
              href="/voice"
              className="text-sm font-medium text-on-surface-variant hover:text-primary transition-colors font-headline tracking-tight"
            >
              Voice Lab
            </a>
          </div>

          <div className="flex items-center gap-4">
            {/* FIX: "Analyze Threat" now opens the Quick Analyze modal */}
            <button
              id="navbar-analyze-threat"
              onClick={() => setShowModal(true)}
              className="bg-primary text-black font-bold px-6 py-2 rounded-lg hover:bg-primary-dark transition-all active:scale-95 duration-150 ease-in-out font-headline text-sm"
            >
              Analyze Threat
            </button>
            <button
              className="md:hidden text-on-background"
              onClick={() => setMobileOpen((v) => !v)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {mobileOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="md:hidden bg-background/95 backdrop-blur-xl border-t border-outline/10 px-6 pb-4 overflow-hidden"
            >
              {[['Product', '#product'], ['Tech Stack', '#tech-stack'], ['Impact', '#impact']].map(([label, href]) => (
                <a
                  key={label}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className="block py-3 text-sm font-medium text-on-surface-variant hover:text-primary transition-colors font-headline"
                >
                  {label}
                </a>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div className={`bg-gradient-to-r from-transparent via-primary/20 to-transparent h-[1px] w-full absolute bottom-0 transition-opacity duration-500 ${isScrolled ? 'opacity-100' : 'opacity-0'}`} />
      </nav>

      {/* Quick Analyze Modal */}
      <AnimatePresence>
        {showModal && <QuickAnalyzeModal onClose={() => setShowModal(false)} />}
      </AnimatePresence>
    </>
  );
};
