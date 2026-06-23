"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Globe, Mic, FileText, Mail, ShieldCheck, Box, Activity, Lock, Cpu } from 'lucide-react';

const features = [
  {
    icon: Globe,
    title: "URL Sandbox",
    description: "Live simulation of malicious URLs using Playwright clusters to detect zero-day phishing kits.",
    tag: "PLAYWRIGHT",
    size: "col-span-1 md:col-span-2",
  },
  {
    icon: Mic,
    title: "Voice Deepfake",
    description: "Spectral analysis to identify non-human resonance patterns.",
    tag: "WHISPER",
    size: "col-span-1",
  },
  {
    icon: ShieldCheck,
    title: "Credential Scanner",
    description: "PII detection using Microsoft Presidio to prevent data leakage.",
    tag: "PRESIDIO",
    size: "col-span-1",
  },
  {
    icon: FileText,
    title: "File Security",
    description: "Multi-engine malware scanning with YARA and ClamAV.",
    tag: "YARA / CLAMAV",
    size: "col-span-1 md:col-span-2",
  },
  {
    icon: Mail,
    title: "Email Intelligence",
    description: "IMAP monitoring with natural language understanding of intent.",
    tag: "IMAP SECURE",
    size: "col-span-1",
  },
  {
    icon: Box,
    title: "API Integration",
    description: "Deploy as a proxy or sidecar in under 15 minutes.",
    tag: "API FIRST",
    size: "col-span-1",
  }
];

export const FeatureGrid = () => {
  return (
    <section id="product" className="py-24 px-6 bg-surface-container-lowest">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col items-center mb-20 text-center space-y-4">
          <motion.h2 
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="text-primary font-headline font-bold uppercase tracking-[0.3em] text-sm"
          >
            Sovereign Guard
          </motion.h2>
          <motion.h3 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-4xl md:text-6xl font-headline font-bold text-white tracking-tight"
          >
            Defensive <span className="text-primary italic">Modules</span>.
          </motion.h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {features.map((feature, idx) => (
            <motion.div 
              key={idx}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              whileHover={{ y: -8, borderColor: 'rgba(49, 227, 104, 0.4)' }}
              className={`group p-8 rounded-3xl glass-panel relative overflow-hidden transition-all hover:bg-surface-high border-b-2 border-outline/10 ${feature.size}`}
            >
              <div className="relative z-10">
                <div className="w-14 h-14 bg-primary/10 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform border border-primary/20">
                  <feature.icon className="w-7 h-7 text-primary" />
                </div>
                <h4 className="text-2xl font-headline font-bold text-white mb-3 tracking-tight">{feature.title}</h4>
                <p className="text-on-surface-variant text-sm mb-6 leading-relaxed font-light">{feature.description}</p>
                <div className="flex items-center gap-4">
                  <div className="text-[10px] font-headline text-primary bg-primary/10 px-3 py-1.5 rounded-full font-bold tracking-widest border border-primary/20">
                    {feature.tag}
                  </div>
                  <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                    <span className="text-[8px] text-primary/60 font-bold uppercase tracking-widest">Active</span>
                  </div>
                </div>
              </div>

              {/* Decorative Background Elements */}
              <div className="absolute top-0 right-0 p-8 opacity-5 group-hover:opacity-10 transition-opacity">
                <feature.icon className="w-32 h-32 text-primary" />
              </div>
              <div className="absolute bottom-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/20 to-transparent" />
            </motion.div>
          ))}

          {/* Dynamic Status Card (Bento Filler) */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            className="md:col-span-1 bg-surface rounded-3xl p-8 border border-outline/10 flex flex-col justify-between group hover:border-primary/20 transition-all"
          >
            <div className="space-y-4">
              <p className="text-[10px] font-headline text-on-surface-variant font-bold uppercase tracking-[0.2em]">Neural Status</p>
              <div className="flex items-center gap-3">
                <div className="p-3 bg-secondary-fixed/10 rounded-xl">
                  <Cpu className="text-primary w-6 h-6 animate-spin" style={{ animationDuration: '4s' }} />
                </div>
                <div className="space-y-1">
                  <p className="text-xl font-headline font-bold text-white">99.8% Integrity</p>
                  <p className="text-[10px] text-on-surface-variant font-light">Global nodes synchronized</p>
                </div>
              </div>
            </div>
            
            <div className="pt-8 flex flex-wrap gap-2">
              {['AWS', 'Azure', 'GCP', 'On-Prem'].map((cloud) => (
                <div key={cloud} className="text-[8px] font-headline text-white/40 bg-background px-2 py-1 rounded border border-outline/5">
                  {cloud}
                </div>
              ))}
            </div>
          </motion.div>

        </div>
      </div>
    </section>
  );
};
