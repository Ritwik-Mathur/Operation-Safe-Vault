"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Database, Cpu, Share2, AlertCircle, Terminal } from 'lucide-react';

export const Architecture = () => {
  return (
    <section id="tech-stack" className="py-24 bg-surface-container-lowest px-6 overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <div className="mb-20 space-y-4">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-4xl md:text-5xl font-headline font-bold text-white tracking-tight"
          >
            The Neural <span className="text-primary italic">Backbone</span>.
          </motion.h2>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-on-surface-variant max-w-2xl font-light text-lg"
          >
            A multi-layered pipeline designed for sub-second classification and terminal-level detonation.
          </motion.p>
        </div>

        <div className="glass-panel p-12 rounded-[3rem] border border-outline/20 relative shadow-2xl relative overflow-hidden bg-black/40">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-16 items-center relative z-10">
            {/* Input Layer */}
            <div className="space-y-6">
              <motion.div 
                whileHover={{ x: 10, borderColor: 'rgba(49, 227, 104, 0.4)' }}
                className="p-6 bg-surface rounded-2xl border-l-[6px] border-primary shadow-xl cursor-default transition-all"
              >
                <div className="flex items-center gap-3 mb-2 font-headline font-bold text-white">
                  <Share2 className="w-5 h-5 text-primary" />
                  Multi-source Input
                </div>
                <p className="text-xs text-on-surface-variant font-light">Ingestion of Voice, URL, and Text streams.</p>
              </motion.div>
              
              <motion.div 
                className="p-6 bg-background/50 rounded-2xl border border-outline/10 opacity-60"
              >
                <div className="flex items-center gap-3 mb-2 font-headline font-bold text-white">
                  <Terminal className="w-5 h-5 text-primary/40" />
                  Feature Extraction
                </div>
                <p className="text-xs text-on-surface-variant font-light">Vectorization of semantic properties.</p>
              </motion.div>
            </div>

            {/* Central Engine */}
            <div className="flex justify-center relative">
              <motion.div 
                animate={{ rotate: 360 }}
                transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
                className="absolute inset-0 flex items-center justify-center opacity-20 pointer-events-none"
              >
                <div className="w-[400px] h-[400px] border border-primary/30 rounded-full" />
                <div className="w-[300px] h-[300px] border border-primary/10 rounded-full" />
              </motion.div>

              <div className="relative group">
                <motion.div 
                  animate={{ scale: [1, 1.05, 1] }}
                  transition={{ duration: 4, repeat: Infinity }}
                  className="h-56 w-56 bg-primary/10 rounded-full flex items-center justify-center border-2 border-primary/40 shadow-[0_0_60px_rgba(49,227,104,0.1)] relative z-10"
                >
                  <Cpu className="w-24 h-24 text-primary animate-pulse" />
                </motion.div>
                <div className="absolute -bottom-8 left-1/2 -translate-x-1/2 bg-primary text-black font-headline font-bold px-4 py-1.5 rounded-full text-xs whitespace-nowrap tracking-widest shadow-[0_0_15px_rgba(49,227,104,0.4)]">
                  CLASSIFICATION ENGINE
                </div>
              </div>
            </div>

            {/* Output Layer */}
            <div className="space-y-6">
              <motion.div 
                whileHover={{ x: -10, borderColor: 'rgba(49, 227, 104, 0.4)' }}
                className="p-6 bg-surface rounded-2xl border-r-[6px] border-primary text-right shadow-xl cursor-default transition-all"
              >
                <div className="flex items-center gap-3 justify-end mb-2 font-headline font-bold text-white">
                  Classification Engine
                  <Database className="w-5 h-5 text-primary" />
                </div>
                <p className="text-xs text-on-surface-variant font-light">XGBoost & ChromaDB vector search.</p>
              </motion.div>
              
              <motion.div 
                className="p-6 bg-background/50 rounded-2xl border border-outline/10 opacity-60 text-right"
              >
                <div className="flex items-center gap-3 justify-end mb-2 font-headline font-bold text-white">
                  Real-time Alert
                  <AlertCircle className="w-5 h-5 text-primary/40" />
                </div>
                <p className="text-xs text-on-surface-variant font-light">Push notifications and auto-blocking.</p>
              </motion.div>
            </div>
          </div>

          {/* Tech Logos Stream */}
          <div className="mt-24 pt-12 border-t border-outline/10">
            <div className="flex flex-wrap justify-center gap-12 text-on-surface-variant/40 font-headline font-bold text-xs uppercase tracking-[0.2em] grayscale hover:grayscale-0 transition-all duration-700">
              {['Python 3.13', 'XGBoost', 'ChromaDB', 'Next.js 14', 'FastAPI', 'Docker', 'PostgreSQL'].map((tech) => (
                <div key={tech} className="hover:text-primary transition-colors cursor-default">{tech}</div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
