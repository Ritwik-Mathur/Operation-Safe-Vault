"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, AlertTriangle, Fingerprint, Activity } from 'lucide-react';

const stats = [
  {
    label: "YoY Growth in India",
    value: "142%",
    icon: TrendingUp,
    color: "text-primary"
  },
  {
    label: "Targeted Identities",
    value: "6.8M",
    icon: Fingerprint,
    color: "text-white"
  },
  {
    label: "Click Rate",
    value: "54%",
    icon: Activity,
    color: "text-error"
  }
];

export const CrisisSection = () => {
  return (
    <section id="impact" className="py-24 bg-surface/50 px-6 relative overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-20 gap-8">
          <div className="space-y-4">
            <motion.h2 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-xs font-headline text-primary tracking-[0.3em] uppercase font-bold"
            >
              The Global Crisis
            </motion.h2>
            <motion.h3 
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: 0.1 }}
              className="text-4xl md:text-5xl font-headline font-bold text-white tracking-tight"
            >
              A Silent Digital <span className="text-error">Pandemic</span>.
            </motion.h3>
          </div>
          <motion.p 
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="max-w-md text-on-surface-variant font-light leading-relaxed"
          >
            Modern adversaries leverage LLMs and deepfake diffusion models to bypass legacy security. Traditional blacklists are obsolete.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
          {/* Main Crisis Card */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="md:col-span-8 glass-panel p-10 rounded-2xl relative overflow-hidden group border border-outline/10 hover:border-primary/20 transition-all"
          >
            <div className="relative z-10 space-y-8">
              <div className="w-14 h-14 bg-error/10 rounded-xl flex items-center justify-center border border-error/20">
                <AlertTriangle className="text-error w-8 h-8" />
              </div>
              <div className="space-y-4">
                <h4 className="text-white text-3xl font-headline font-bold tracking-tight">₹70,000 Crore Annual Loss</h4>
                <p className="text-on-surface-variant leading-relaxed max-w-xl text-lg font-light">
                  In India alone, AI-driven scams have ballooned into a multi-billion dollar crisis. Sophisticated synthetic identities and voice clones have rendered traditional ID verification obsolete.
                </p>
              </div>
              
              <div className="pt-10 border-t border-outline/10 flex flex-wrap gap-16">
                {stats.map((stat, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className={`text-4xl font-headline font-bold ${stat.color} flex items-center gap-2`}>
                      <stat.icon className="w-6 h-6 opacity-60" />
                      {stat.value}
                    </div>
                    <div className="text-[10px] font-headline text-on-surface-variant uppercase tracking-[0.2em] font-bold">
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Background Grid Accent */}
            <div className="absolute inset-0 bg-[radial-gradient(#ff4b4b_1px,transparent_1px)] [background-size:32px_32px] opacity-5 pointer-events-none" />
          </motion.div>

          {/* Voice Cloning Card */}
          <motion.div 
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2 }}
            className="md:col-span-4 bg-surface border border-outline/10 p-10 rounded-2xl flex flex-col justify-between group hover:border-primary/20 transition-all"
          >
            <div className="space-y-6">
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center border border-primary/20">
                <Activity className="text-primary w-6 h-6" />
              </div>
              <h4 className="text-white text-2xl font-headline font-bold tracking-tight">Voice Cloning</h4>
              <p className="text-on-surface-variant font-light">
                Scammers replicate family members' voices with just 3 seconds of audio sample, achieving 95% emotional accuracy.
              </p>
            </div>
            
            <div className="mt-12 p-4 rounded-xl bg-black/40 border border-outline/10">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2 h-2 rounded-full bg-error animate-pulse" />
                <span className="text-[10px] font-headline text-error uppercase tracking-widest font-bold">Active Deepfake Detected</span>
              </div>
              <div className="flex gap-1.5 h-12 items-end">
                {[40, 70, 45, 90, 60, 80, 30, 65, 50, 75].map((h, i) => (
                  <motion.div 
                    key={i}
                    animate={{ height: [`${h}%`, `${h+10}%`, `${h}%`] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.1 }}
                    className="flex-1 bg-primary/80 rounded-t-sm"
                  />
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
