"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Mail, Shield, ShieldAlert, ShieldCheck, 
  Search, Lock, Key, Server, 
  ChevronRight, AlertTriangle, ArrowLeft,
  MailOpen, ExternalLink, RefreshCw
} from 'lucide-react';
import { Navbar } from "@/components/Navbar";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

interface EmailResult {
  email_id: string;
  from: string;
  subject: string;
  date: string;
  analysis: {
    score: number;
    verdict: string;
    reasons: string[];
    source: string;
  };
}

export default function InboxPage() {
  const [host, setHost] = useState('imap.gmail.com');
  const [email, setEmail] = useState('');
  const [pass, setPass] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<EmailResult[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const fd = new URLSearchParams();
      fd.append('imap_host', host);
      fd.append('email_addr', email);
      fd.append('password', pass);
      fd.append('count', '15');

      const res = await fetch(`${API_BASE}/email/scan-inbox`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: fd
      });

      if (!res.ok) throw new Error(`Connection failed: ${res.status}`);
      const data = await res.json();
      
      if (data.results && data.results.length > 0) {
        setResults(data.results);
        setIsConnected(true);
      } else {
        throw new Error("No emails found or access denied.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to connect to IMAP server.");
    } finally {
      setLoading(false);
    }
  };

  const selectedEmail = results.find(r => r.email_id === selectedId);

  const getScoreColor = (score: number) => {
    if (score >= 70) return 'text-error';
    if (score >= 45) return 'text-orange-400';
    return 'text-primary';
  };

  const getVerdictBg = (score: number) => {
    if (score >= 70) return 'bg-error/10 border-error/20';
    if (score >= 45) return 'bg-orange-400/10 border-orange-400/20';
    return 'bg-primary/10 border-primary/20';
  };

  return (
    <main className="min-h-screen bg-background relative overflow-hidden">
      <div className="fixed inset-0 noise-overlay opacity-[0.03] pointer-events-none" />
      <Navbar />

      <div className="pt-32 pb-12 px-6 max-w-7xl mx-auto h-screen flex flex-col">
        {!isConnected ? (
          <div className="flex-1 flex items-center justify-center">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass-panel p-10 rounded-[2.5rem] border border-outline/10 w-full max-w-xl bg-surface/30 backdrop-blur-3xl shadow-2xl"
            >
              <div className="flex flex-col items-center text-center space-y-6 mb-10">
                <div className="w-20 h-20 bg-primary/10 rounded-3xl flex items-center justify-center border border-primary/20 shadow-[0_0_40px_rgba(49,227,104,0.1)]">
                  <Mail className="w-10 h-10 text-primary" />
                </div>
                <div className="space-y-2">
                  <h1 className="text-4xl font-headline font-bold text-white tracking-tight">Email Intelligence</h1>
                  <p className="text-on-surface-variant font-light max-w-md">
                    Connect your IMAP inbox to synchronize real-time threat monitoring and neural scam detection across your messages.
                  </p>
                </div>
              </div>

              <form onSubmit={handleConnect} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <label className="text-[10px] uppercase font-headline font-bold text-primary tracking-widest ml-1">IMAP Host</label>
                    <div className="relative group">
                      <Server className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/40 group-focus-within:text-primary transition-colors" />
                      <input 
                        value={host}
                        onChange={e => setHost(e.target.value)}
                        className="w-full bg-black/40 border border-outline/20 rounded-2xl py-4 pl-12 pr-6 text-white focus:outline-none focus:border-primary/50 transition-all font-light text-sm"
                        placeholder="imap.gmail.com"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="text-[10px] uppercase font-headline font-bold text-primary tracking-widest ml-1">Email Address</label>
                    <div className="relative group">
                      <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/40 group-focus-within:text-primary transition-colors" />
                      <input 
                        type="email"
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        className="w-full bg-black/40 border border-outline/20 rounded-2xl py-4 pl-12 pr-6 text-white focus:outline-none focus:border-primary/50 transition-all font-light text-sm"
                        placeholder="you@gmail.com"
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] uppercase font-headline font-bold text-primary tracking-widest ml-1">App Password</label>
                  <div className="relative group">
                    <Key className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant/40 group-focus-within:text-primary transition-colors" />
                    <input 
                      type="password"
                      value={pass}
                      onChange={e => setPass(e.target.value)}
                      className="w-full bg-black/40 border border-outline/20 rounded-2xl py-4 pl-12 pr-6 text-white focus:outline-none focus:border-primary/50 transition-all font-light text-sm"
                      placeholder="••••••••••••••••"
                    />
                  </div>
                  <p className="text-[10px] text-on-surface-variant/40 mt-3 flex items-center gap-2">
                    <AlertTriangle className="w-3 h-3 text-orange-400" />
                    For Gmail, use a 16-character App Password. 
                    <a href="https://myaccount.google.com/apppasswords" target="_blank" className="text-primary hover:underline ml-1">Get one here.</a>
                  </p>
                </div>

                {error && (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="p-4 rounded-xl bg-error/10 border border-error/20 text-error text-xs text-center"
                  >
                    {error}
                  </motion.div>
                )}

                <button 
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary text-black font-headline font-bold py-5 rounded-2xl shadow-xl shadow-primary/20 hover:bg-primary-dark transition-all disabled:opacity-50 flex items-center justify-center gap-3 active:scale-[0.98]"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-5 h-5 animate-spin" />
                      ESTABLISHING SECURE CHANNEL
                    </>
                  ) : (
                    <>
                      SYNCHRONIZE INBOX
                      <Lock className="w-5 h-5" />
                    </>
                  )}
                </button>
              </form>
            </motion.div>
          </div>
        ) : (
          <div className="flex-1 flex gap-6 overflow-hidden">
            {/* Sidebar List */}
            <motion.div 
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="w-1/3 glass-panel rounded-3xl border border-outline/10 overflow-hidden flex flex-col bg-surface/20"
            >
              <div className="p-6 border-b border-outline/10 flex justify-between items-center bg-surface/30">
                <div className="space-y-1">
                  <h2 className="text-sm font-headline font-bold text-white uppercase tracking-widest">Sovereign Inbox</h2>
                  <p className="text-[10px] text-primary font-bold uppercase tracking-widest flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                    Live Monitoring
                  </p>
                </div>
                <button 
                  onClick={() => setIsConnected(false)}
                  className="p-2 rounded-xl border border-outline/10 hover:bg-white/5 transition-colors"
                >
                  <ArrowLeft className="w-4 h-4 text-on-surface-variant" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
                {results.map((em) => {
                  const score = em.analysis.score;
                  const isSelected = selectedId === em.email_id;
                  return (
                    <motion.div
                      key={em.email_id}
                      onClick={() => setSelectedId(em.email_id)}
                      whileHover={{ scale: 1.01, x: 4 }}
                      whileTap={{ scale: 0.98 }}
                      className={`p-4 rounded-2xl border transition-all cursor-pointer relative overflow-hidden ${
                        isSelected 
                          ? 'bg-primary/10 border-primary shadow-lg shadow-primary/5' 
                          : 'bg-black/20 border-white/5 hover:border-white/20'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-2">
                        <p className={`text-xs font-bold truncate max-w-[150px] ${isSelected ? 'text-primary' : 'text-white'}`}>
                          {em.subject || '(No Subject)'}
                        </p>
                        <span className={`text-xs font-headline font-bold ${getScoreColor(score)}`}>
                          {score}
                        </span>
                      </div>
                      <p className="text-[10px] text-on-surface-variant truncate mb-3">{em.from}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] text-on-surface-variant/40 font-mono italic">{em.date.split(' ').slice(0, 4).join(' ')}</span>
                        <div className={`text-[8px] uppercase font-bold tracking-widest px-2 py-0.5 rounded border ${
                          score >= 70 ? 'bg-error/10 text-error border-error/20' : 
                          score >= 45 ? 'bg-orange-400/10 text-orange-400 border-orange-400/20' :
                          'bg-primary/10 text-primary border-primary/20'
                        }`}>
                          {em.analysis.verdict}
                        </div>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            </motion.div>

            {/* Detailed View */}
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex-1 glass-panel rounded-3xl border border-outline/10 flex flex-col bg-surface/20 relative"
            >
              <AnimatePresence mode="wait">
                {!selectedId ? (
                  <motion.div 
                    key="empty"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-6"
                  >
                    <div className="w-24 h-24 rounded-full border-2 border-dashed border-outline/20 flex items-center justify-center">
                      <MailOpen className="w-10 h-10 text-on-surface-variant/20" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-xl font-headline font-bold text-white/50">Select an Analysis</h3>
                      <p className="text-sm text-on-surface-variant/30 max-w-xs font-light">
                        Choose a message from your synchronized inbox to initiate deep neural forensic analysis.
                      </p>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div 
                    key="detail"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="flex-1 flex flex-col overflow-hidden"
                  >
                    {/* Detail Header */}
                    <div className="p-8 border-b border-outline/10 bg-surface/30">
                      <div className="flex justify-between items-start mb-6">
                        <div className="space-y-2">
                          <h2 className="text-3xl font-headline font-bold text-white tracking-tight">{selectedEmail?.subject}</h2>
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20">
                              <Shield className="w-4 h-4 text-primary" />
                            </div>
                            <div>
                              <p className="text-sm text-white font-medium">{selectedEmail?.from}</p>
                              <p className="text-[10px] text-on-surface-variant">{selectedEmail?.date}</p>
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2 text-right">
                          <div className={`px-6 py-3 rounded-2xl border-2 flex flex-col items-end ${getVerdictBg(selectedEmail?.analysis.score || 0)}`}>
                            <span className={`text-4xl font-headline font-bold ${getScoreColor(selectedEmail?.analysis.score || 0)}`}>
                              {selectedEmail?.analysis.score}
                            </span>
                            <span className="text-[10px] font-headline font-bold uppercase tracking-widest">{selectedEmail?.analysis.verdict}</span>
                          </div>
                          <p className="text-[9px] text-on-surface-variant/40 uppercase tracking-widest font-black">Neural Threat Index</p>
                        </div>
                      </div>
                    </div>

                    {/* Detail Content */}
                    <div className="flex-1 overflow-y-auto p-8 space-y-12 custom-scrollbar">
                      {/* Analysis Reasons */}
                      <section className="space-y-6">
                        <div className="flex items-center gap-2">
                          <Search className="w-4 h-4 text-primary" />
                          <h4 className="text-[10px] font-headline font-bold text-primary uppercase tracking-[0.2em]">Forensic Findings</h4>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {selectedEmail?.analysis.reasons.map((r, i) => (
                            <motion.div 
                              key={i}
                              initial={{ opacity: 0, scale: 0.95 }}
                              animate={{ opacity: 1, scale: 1 }}
                              transition={{ delay: i * 0.05 }}
                              className="p-4 rounded-xl bg-black/30 border border-white/5 flex gap-3 items-start"
                            >
                              <AlertTriangle className="w-4 h-4 text-orange-400 shrink-0 mt-0.5" />
                              <p className="text-xs text-on-surface-variant font-light leading-relaxed">{r}</p>
                            </motion.div>
                          ))}
                          {selectedEmail?.analysis.reasons.length === 0 && (
                            <div className="col-span-2 p-8 rounded-2xl border border-primary/10 bg-primary/5 flex flex-col items-center justify-center text-center space-y-3">
                              <ShieldCheck className="w-8 h-8 text-primary" />
                              <p className="text-sm font-medium text-primary">No immediate threat vectors detected in headers.</p>
                            </div>
                          )}
                        </div>
                      </section>

                      {/* Call to Action */}
                      <section className="pt-12 border-t border-outline/10 flex justify-between items-center">
                        <div className="space-y-1">
                          <h4 className="text-white font-bold text-sm">Recommended Action</h4>
                          <p className="text-xs text-on-surface-variant font-light">
                            { (selectedEmail?.analysis.score || 0) >= 70 
                              ? "CRITICAL: Do not interact with links or provide sensitive data."
                              : "EXERCISE CAUTION: Standard verification suggested for unknown senders."}
                          </p>
                        </div>
                        <div className="flex gap-4">
                          <button className="px-6 py-3 rounded-xl border border-outline/20 bg-surface text-white text-xs font-bold hover:bg-white/5 transition-colors">
                            WHITE-LIST SENDER
                          </button>
                          <button className={`px-6 py-3 rounded-xl font-bold text-xs shadow-lg transition-all active:scale-[0.98] ${
                            (selectedEmail?.analysis.score || 0) >= 70 ? 'bg-error text-black shadow-error/20' : 'bg-primary text-black shadow-primary/20'
                          }`}>
                            {(selectedEmail?.analysis.score || 0) >= 70 ? 'PROTOCOL LOCKOUT' : 'SAFE ARCHIVE'}
                          </button>
                        </div>
                      </section>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          </div>
        )}
      </div>

      {/* Background Gradients */}
      <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-primary/5 rounded-full blur-[150px] -z-10" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-secondary/5 rounded-full blur-[120px] -z-10" />
    </main>
  );
}
