"use client";

import React, { useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Activity, RefreshCw } from "lucide-react";

interface SpectrogramPanelProps {
  /** base64 data URI  e.g. "data:image/png;base64,..." — null while pending */
  src: string | null;
  /** Label shown in the header  */
  label?: string;
  /** Show a "live update" pulse badge (for WebSocket chunks) */
  live?: boolean;
  /** Optional chunk number that produced this image */
  chunkNumber?: number;
}

export const SpectrogramPanel: React.FC<SpectrogramPanelProps> = ({
  src,
  label = "Audio Spectrogram Analysis",
  live = false,
  chunkNumber,
}) => {
  return (
    <div className="glass-panel rounded-2xl border border-outline/20 overflow-hidden shadow-[0_0_40px_rgba(49,227,104,0.04)] bg-black/40">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-outline/10 bg-surface/30">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" />
          <span className="text-[10px] font-headline font-bold text-on-surface-variant uppercase tracking-widest">
            {label}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {chunkNumber !== undefined && (
            <span className="text-[9px] font-mono text-on-surface-variant/50">
              chunk #{chunkNumber}
            </span>
          )}
          {live && (
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
              <span className="text-[8px] font-headline font-bold text-primary uppercase tracking-widest">
                Live
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="relative min-h-[140px] flex items-center justify-center p-3">
        <AnimatePresence mode="wait">
          {src ? (
            <motion.img
              key={src.slice(-20)}          /* animate on each new image     */
              src={src}
              alt="Mel-spectrogram of the analysed audio"
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
              className="w-full rounded-xl object-contain"
              style={{ imageRendering: "auto" }}
            />
          ) : (
            <motion.div
              key="placeholder"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-3 py-8"
            >
              <RefreshCw className="w-7 h-7 text-on-surface-variant/20 animate-spin" />
              <p className="text-[10px] text-on-surface-variant/30 font-light">
                {live ? "Waiting for next spectrogram frame…" : "Generating spectrogram…"}
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* green shimmer border when live + image present */}
        {live && src && (
          <div className="absolute inset-0 rounded-2xl pointer-events-none ring-1 ring-primary/20" />
        )}
      </div>

      {/* ── Footer note ────────────────────────────────────────────────────── */}
      <div className="px-5 py-2 border-t border-outline/5 bg-surface/10">
        <p className="text-[9px] text-on-surface-variant/30 font-light">
          Mel-spectrogram · magma colormap · 64 mel bands · 16 kHz
        </p>
      </div>
    </div>
  );
};
