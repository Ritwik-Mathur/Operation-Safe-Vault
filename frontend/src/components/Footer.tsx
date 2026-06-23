"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { User, Github, Linkedin, Shield } from 'lucide-react';

const team = [
  { name: "Ritwik Mathur", id: "RA2311003010766" },
  { name: "Pragya Paramita Sahoo", id: "RA2311003010770" },
  { name: "Rishika Sarkar", id: "RA2311003010721" },
  { name: "Devansh Gupta", id: "RA2311003010722" },
];

export const TeamSection = () => {
  return (
    <section className="py-24 bg-surface px-6 relative overflow-hidden">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-20 space-y-4">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-4xl md:text-5xl font-headline font-bold text-white tracking-tight"
          >
            Command <span className="text-primary italic">Center</span>.
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.1 }}
            className="text-on-surface-variant max-w-2xl mx-auto font-light"
          >
            The architects behind the Phish Police sovereignty protocol.
          </motion.p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
          {team.map((member, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: idx * 0.1 }}
              whileHover={{ y: -10 }}
              className="p-8 rounded-3xl glass-panel text-center group border-outline/10 hover:border-primary/30 transition-all bg-black/40"
            >
              <div className="w-24 h-24 bg-surface-high rounded-full mx-auto mb-8 flex items-center justify-center border-2 border-outline/20 group-hover:border-primary transition-all">
                <User className="w-12 h-12 text-on-surface-variant/40 group-hover:text-primary transition-all" />
              </div>
              <h5 className="font-headline font-bold text-xl text-white mb-2 tracking-tight group-hover:text-primary transition-colors">{member.name}</h5>
              <div className="text-[10px] font-headline text-primary bg-primary/10 px-3 py-1 rounded-full inline-block font-bold tracking-widest border border-primary/20 mb-6">
                {member.id}
              </div>

              <div className="flex justify-center gap-4 text-on-surface-variant/40">
                <Github className="w-5 h-5 hover:text-white cursor-pointer transition-colors" />
                <Linkedin className="w-5 h-5 hover:text-white cursor-pointer transition-colors" />
                <Shield className="w-5 h-5 hover:text-primary cursor-pointer transition-colors" />
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

export const Footer = () => {
  return (
    <footer className="w-full py-16 border-t border-outline/10 bg-[#0e0e0e] px-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-start gap-12 mb-16">
          <div className="space-y-6">
            <div className="text-2xl font-bold tracking-tighter text-primary font-headline flex items-center gap-2">
              <Shield className="w-6 h-6" />
              PHISH POLICE
            </div>
            <p className="max-w-xs text-on-surface-variant text-sm font-light leading-relaxed">
              The world's first autonomous AI-powered defense system against synthetic fraud and adversarial social engineering.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-12">
            <div className="space-y-4">
              <p className="text-xs font-headline text-white font-bold uppercase tracking-widest">Protocol</p>
              <ul className="space-y-2 text-sm text-on-surface-variant font-light">
                <li className="hover:text-primary cursor-pointer transition-colors">Documentation</li>
                <li className="hover:text-primary cursor-pointer transition-colors">Neural Assets</li>
                <li className="hover:text-primary cursor-pointer transition-colors">System Status</li>
              </ul>
            </div>
            <div className="space-y-4">
              <p className="text-xs font-headline text-white font-bold uppercase tracking-widest">Company</p>
              <ul className="space-y-2 text-sm text-on-surface-variant font-light">
                <li className="hover:text-primary cursor-pointer transition-colors">Legal</li>
                <li className="hover:text-primary cursor-pointer transition-colors">Privacy Policy</li>
                <li className="hover:text-primary cursor-pointer transition-colors">Security Audit</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="pt-8 border-t border-outline/10 flex flex-col md:flex-row justify-between items-center gap-4 text-[10px] font-headline text-on-surface-variant uppercase tracking-[0.2em] font-bold">
          <div>© 2024 PHISH POLICE. ALL RIGHTS RESERVED.</div>
          <div className="flex gap-8">
            <span className="hover:text-primary cursor-pointer transition-colors">Designed for Absolute Precision</span>
            <span className="hover:text-primary cursor-pointer transition-colors">v4.2.0-STABLE</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
