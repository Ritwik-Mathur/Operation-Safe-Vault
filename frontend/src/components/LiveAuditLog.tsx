"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal, Shield, AlertTriangle, CheckCircle2, CloudLightning } from 'lucide-react';

const mockLogs = [
  { type: 'info', msg: '[SCAN] INCOMING Voice Call detected from 182.xx.xx.4' },
  { type: 'warning', msg: '[THREAT] Synthetic Voice signature identified (92% match)' },
  { type: 'success', msg: '[BLOCK] Call routed to Adversarial Buffer. Neutralized.' },
  { type: 'info', msg: '[SCAN] URL Sandbox detonation: bit.ly/secure-login-34' },
  { type: 'error', msg: '[ALERT] Zero-day Phishing kit detected (Level 4)' },
  { type: 'success', msg: '[PURGE] Domain blacklisted across all sovereign nodes.' },
  { type: 'info', msg: '[SCAN] File attachment analysis: invoice_3942.pdf.exe' },
  { type: 'error', msg: '[THREAT] Obfuscated shellcode detected in PDF stream.' },
  { type: 'success', msg: '[BLOCK] Attachment quarantined. User notified.' },
];

export const LiveAuditLog = () => {
  const [logs, setLogs] = useState(mockLogs.slice(0, 4));

  useEffect(() => {
    const interval = setInterval(() => {
      setLogs((prev) => {
        const nextLog = mockLogs[Math.floor(Math.random() * mockLogs.length)];
        const newLogs = [...prev.slice(1), nextLog];
        return newLogs;
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-full max-w-2xl mx-auto glass-panel rounded-2xl overflow-hidden border border-outline/10 shadow-2xl bg-black/60 relative group">
      <div className="px-6 py-3 border-b border-outline/10 flex justify-between items-center bg-surface/30">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-primary" />
          <span className="text-[10px] font-headline text-on-surface-variant font-bold tracking-widest uppercase">Live Security Audit Log</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
          <span className="text-[8px] font-headline text-primary font-bold uppercase tracking-widest">Active Monitoring</span>
        </div>
      </div>
      
      <div className="p-6 font-mono text-[10px] sm:text-xs min-h-[160px] flex flex-col gap-3">
        <AnimatePresence mode="popLayout">
          {logs.map((log, idx) => (
            <motion.div 
              key={`${log.msg}-${idx}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.5 }}
              className="flex items-start gap-4 group/item"
            >
              <span className="text-on-surface-variant/30 select-none">
                {new Date().toLocaleTimeString([], { hour12: false })}
              </span>
              <div className="flex gap-2">
                {log.type === 'info' && <CloudLightning className="w-3.5 h-3.5 text-blue-400 mt-0.5" />}
                {log.type === 'warning' && <AlertTriangle className="w-3.5 h-3.5 text-orange-400 mt-0.5" />}
                {log.type === 'error' && <Shield className="w-3.5 h-3.5 text-error mt-0.5" />}
                {log.type === 'success' && <CheckCircle2 className="w-3.5 h-3.5 text-primary mt-0.5" />}
                
                <p className={`${
                  log.type === 'error' ? 'text-error' : 
                  log.type === 'warning' ? 'text-orange-400' : 
                  log.type === 'success' ? 'text-primary' : 
                  'text-on-surface-variant'
                } leading-relaxed font-medium`}>
                  {log.msg}
                </p>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Gloss Effect */}
      <div className="absolute inset-0 pointer-events-none bg-gradient-to-t from-black/20 to-transparent" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-20%,rgba(49,227,104,0.05),transparent)] pointer-events-none" />
    </div>
  );
};
