"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Mail, Phone, Link, File, Video, MessageSquare } from 'lucide-react';

const channels = [
  { icon: MessageSquare, label: "Text" },
  { icon: Mail, label: "Email" },
  { icon: Link, label: "URL" },
  { icon: Phone, label: "Voice" },
  { icon: Video, label: "Video" },
  { icon: File, label: "File" },
];

export const OneShieldSolution = () => {
  return (
    <section className="py-24 relative overflow-hidden bg-background">
      {/* Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[radial-gradient(circle_at_center,rgba(49,227,104,0.05),transparent_70%)]" />

      <div className="max-w-7xl mx-auto px-6 relative">
        <div className="text-center mb-20 space-y-4">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-4xl md:text-6xl font-headline font-bold text-white tracking-tight"
          >
            The <span className="text-primary italic">One Shield</span> Solution.
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-xl text-on-surface-variant max-w-2xl mx-auto font-light"
          >
            Consolidating fragmented security into a single, unbreakable command chain.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Channel Grid */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {channels.map((channel, idx) => (
              <motion.div 
                key={idx}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.05, borderColor: 'rgba(49, 227, 104, 0.4)' }}
                viewport={{ once: true }}
                transition={{ delay: idx * 0.05 }}
                className="p-8 rounded-2xl glass-panel flex flex-col items-center text-center group border-outline/10 transition-all cursor-default"
              >
                <channel.icon className="text-primary w-10 h-10 mb-4 group-hover:scale-110 transition-transform filter drop-shadow-[0_0_5px_rgba(49,227,104,0.3)]" />
                <span className="font-headline font-bold text-white tracking-tight">{channel.label}</span>
              </motion.div>
            ))}
          </div>

          {/* Threat Score Dashboard */}
          <motion.div 
            initial={{ opacity: 0, x: 50 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="bg-surface rounded-3xl p-10 border border-primary/20 shadow-[0_0_50px_rgba(49,227,104,0.1)] relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 p-8">
              <motion.div 
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                className="w-32 h-32 border-2 border-primary/10 border-dashed rounded-full"
              />
            </div>

            <div className="flex justify-between items-start mb-10 relative z-10">
              <div>
                <h3 className="text-3xl font-headline font-bold text-primary mb-2">One Threat Score</h3>
                <p className="text-on-surface-variant font-light">Centralized risk quantification engine.</p>
              </div>
              <div className="h-20 w-20 rounded-full border-4 border-primary/30 flex items-center justify-center bg-primary/5 shadow-[0_0_20px_rgba(49,227,104,0.2)]">
                <span className="text-3xl font-bold font-headline text-primary">98</span>
              </div>
            </div>

            <div className="space-y-8 relative z-10">
              <div className="w-full bg-surface-high h-4 rounded-full overflow-hidden border border-outline/10">
                <motion.div 
                  initial={{ width: 0 }}
                  whileInView={{ width: "98%" }}
                  viewport={{ once: true }}
                  transition={{ duration: 1.5, delay: 0.5 }}
                  className="bg-primary h-full shadow-[0_0_20px_#31e368] relative"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
                </motion.div>
              </div>

              <div className="grid grid-cols-2 gap-6">
                <div className="p-6 bg-background rounded-2xl border border-outline/10 shadow-inner">
                  <div className="text-[10px] font-headline text-on-surface-variant mb-1 uppercase tracking-widest font-bold">LATENCY</div>
                  <div className="font-headline font-bold text-2xl text-white">142ms</div>
                </div>
                <div className="p-6 bg-background rounded-2xl border border-outline/10 shadow-inner">
                  <div className="text-[10px] font-headline text-on-surface-variant mb-1 uppercase tracking-widest font-bold">CONFIDENCE</div>
                  <div className="font-headline font-bold text-2xl text-white">99.9%</div>
                </div>
              </div>

              <div className="p-6 bg-primary/5 rounded-2xl border-l-4 border-primary italic text-on-surface-variant/90 text-sm font-light">
                "System identified high-frequency synthetic audio artifacts consistent with adversarial voice cloning attempts."
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
};
