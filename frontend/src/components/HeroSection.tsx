"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { Shield, ChevronRight, Lock } from 'lucide-react';

export const HeroSection = () => {
  // "Deploy Shield Now" scrolls to the interactive sandbox so users can
  // immediately try the real API. "View Documentation" links to the FastAPI
  // auto-generated docs served by the backend.
  const handleDeploy = () => {
    const el = document.getElementById('sandbox');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  };

  const handleDocs = () => {
    window.open(
      (process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000') + '/docs',
      '_blank',
      'noopener,noreferrer',
    );
  };

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden px-6 hero-gradient pt-20">
      {/* Background Decorative Elements */}
      <div className="absolute inset-0 opacity-20 pointer-events-none">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px]" />
      </div>

      <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center z-10 w-full">
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          className="space-y-8"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-headline uppercase tracking-widest">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
            System Active: Shield Protocol v4.2
          </div>

          <h1 className="text-5xl md:text-7xl font-headline font-bold text-white leading-[1.1] tracking-tight">
            The Sovereign <span className="text-secondary-fixed text-primary italic">Defense</span> Against AI Scammers.
          </h1>

          <p className="text-on-surface-variant text-lg md:text-xl max-w-xl font-light leading-relaxed">
            Fraud Shield AI provides an autonomous defense layer designed to intercept hyper-realistic voice clones and synthetic traps before they reach your network.
          </p>

          <div className="flex flex-wrap gap-4 pt-4">
            {/* FIX: "Deploy Shield Now" scrolls to the live sandbox section */}
            <motion.button
              id="hero-deploy-shield"
              onClick={handleDeploy}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="bg-primary text-black px-8 py-4 rounded-xl font-headline font-bold flex items-center gap-3 shadow-[0_0_20px_rgba(49,227,104,0.3)] transition-shadow"
            >
              Deploy Shield Now
              <Shield className="w-5 h-5" />
            </motion.button>

            {/* FIX: "View Documentation" opens FastAPI /docs in a new tab */}
            <motion.button
              id="hero-view-docs"
              onClick={handleDocs}
              whileHover={{ backgroundColor: 'rgba(255,255,255,0.05)' }}
              className="border border-outline bg-surface/50 backdrop-blur-sm text-white px-8 py-4 rounded-xl font-headline font-medium flex items-center gap-2 transition-colors"
            >
              View Documentation
              <ChevronRight className="w-4 h-4" />
            </motion.button>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1, delay: 0.2 }}
          className="relative group"
        >
          <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 to-primary-dark/20 rounded-2xl blur-2xl opacity-50 group-hover:opacity-100 transition duration-1000"></div>

          <div className="relative glass-panel rounded-2xl overflow-hidden aspect-square flex items-center justify-center border border-outline/30 shadow-2xl">
            <div className="absolute inset-0 bg-[radial-gradient(#31e368_1px,transparent_1px)] [background-size:24px_24px] opacity-10" />

            <motion.div
              animate={{
                rotateY: [0, 10, -10, 0],
                rotateX: [0, -5, 5, 0],
              }}
              transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
              className="relative z-10 p-12 bg-black/40 rounded-full border border-primary/20 backdrop-blur-md shadow-[0_0_50px_rgba(49,227,104,0.15)]"
            >
              <Shield className="w-48 h-48 text-primary opacity-90 filter drop-shadow-[0_0_15px_rgba(49,227,104,0.5)]" />
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                className="absolute inset-0 flex items-center justify-center"
              >
                <div className="w-full h-full border-2 border-primary/30 rounded-full animate-pulse" />
              </motion.div>
            </motion.div>

            <div className="absolute bottom-8 left-8 right-8 p-6 glass-panel rounded-xl border border-primary/20 bg-black/40">
              <div className="flex justify-between items-center mb-4">
                <span className="text-xs font-headline text-primary uppercase tracking-widest font-bold">Threat Vector Analysis</span>
                <span className="text-xs font-headline text-white/50">99.8% ACCURACY</span>
              </div>
              <div className="w-full bg-surface-high h-1.5 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: "94%" }}
                  transition={{ duration: 1.5, delay: 1 }}
                  className="bg-primary h-full shadow-[0_0_10px_rgba(49,227,104,0.8)]"
                />
              </div>
            </div>
          </div>

          {/* Floating Status Cards */}
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 4, repeat: Infinity }}
            className="absolute -top-6 -right-6 glass-panel p-4 rounded-xl border border-primary/30 bg-black/60 shadow-xl hidden md:block"
          >
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Lock className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-[10px] text-primary/60 font-bold uppercase">Encryption</p>
                <p className="text-sm font-bold">Sovereign Mode</p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </section>
  );
};
