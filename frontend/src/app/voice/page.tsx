"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  Mic,
  MicOff,
  ShieldAlert,
  Shield,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Radio,
  Clock,
  Zap,
} from "lucide-react";
import { SpectrogramPanel } from "@/components/SpectrogramPanel";

// ── Types ─────────────────────────────────────────────────────────────────────
interface VoiceResult {
  score: number;
  verdict: string;
  severity: string;
  reasons: string[];
  spectrogram_image: string | null;
  raw?: {
    transcript?: string;
    acoustic_score?: number;
    nlp_score?: number;
    deepfake_score?: number;
    is_deepfake?: boolean;
  };
}

interface LiveChunk {
  chunk_count: number;
  current_score: number;
  verdict: string;
  elapsed_seconds: number;
  high_risk_triggered: boolean;
  time_to_alert_seconds?: number;
  spectrogram_image: string | null;
  reasons: string[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_BASE  = API_BASE.replace(/^http/, "ws");

// ── Helpers ───────────────────────────────────────────────────────────────────
function scoreColor(score: number) {
  if (score >= 80) return "text-error";
  if (score >= 55) return "text-orange-400";
  if (score >= 35) return "text-yellow-400";
  return "text-primary";
}
function scoreBorder(score: number) {
  if (score >= 80) return "border-error";
  if (score >= 55) return "border-orange-400";
  if (score >= 35) return "border-yellow-400";
  return "border-primary";
}
function scoreRing(score: number) {
  if (score >= 80) return "stroke-error";
  if (score >= 55) return "stroke-orange-400";
  return "stroke-primary";
}

// ── WAV Encoding Helpers ──────────────────────────────────────────────────────
function encodeWAV(buffers: Float32Array[], sampleRate: number, numChannels: number = 1): ArrayBuffer {
  const bytesPerSample = 2;
  const numSamples = buffers.reduce((acc, b) => acc + b.length, 0);
  const buffer = new ArrayBuffer(44 + numSamples * bytesPerSample);
  const view = new DataView(buffer);

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + numSamples * bytesPerSample, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numChannels * bytesPerSample, true);
  view.setUint16(32, numChannels * bytesPerSample, true);
  view.setUint16(34, 16, true);
  writeString(view, 36, 'data');
  view.setUint32(40, numSamples * bytesPerSample, true);

  let offset = 44;
  for (const b of buffers) {
    for (let i = 0; i < b.length; i++) {
      let s = Math.max(-1, Math.min(1, b[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
      offset += 2;
    }
  }

  return buffer;
}

function writeString(view: DataView, offset: number, string: string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

// ── Sub-components ────────────────────────────────────────────────────────────
const ScoreDial = ({ score }: { score: number }) => (
  <div className="relative w-36 h-36 flex items-center justify-center">
    <svg className="w-full h-full -rotate-90" viewBox="0 0 144 144">
      <circle cx="72" cy="72" r="60" className="stroke-surface-high fill-none" strokeWidth="8" />
      <motion.circle
        initial={{ strokeDasharray: "0, 1000" }}
        animate={{ strokeDasharray: `${(score / 100) * 377}, 1000` }}
        transition={{ duration: 1.2, ease: "easeOut" }}
        cx="72" cy="72" r="60"
        className={`fill-none ${scoreRing(score)}`}
        strokeWidth="8"
        strokeLinecap="round"
      />
    </svg>
    <div className="absolute inset-0 flex flex-col items-center justify-center">
      <span className={`text-4xl font-headline font-bold ${scoreColor(score)} glow-text`}>{score}</span>
      <span className="text-[8px] font-headline font-bold text-on-surface-variant tracking-widest">RISK SCORE</span>
    </div>
  </div>
);

const ReasonList = ({ reasons }: { reasons: string[] }) => (
  <ul className="space-y-1.5 max-h-40 overflow-y-auto pr-1 scrollbar-thin">
    {reasons.slice(0, 8).map((r, i) => (
      <li key={i} className="flex items-start gap-2 text-[10px] text-on-surface-variant font-light leading-relaxed">
        <Zap className="w-2.5 h-2.5 mt-0.5 text-primary/60 shrink-0" />
        {r}
      </li>
    ))}
  </ul>
);

export default function VoiceAnalyzerPage() {
  // ── Upload tab state ───────────────────────────────────────────────────────
  const [file, setFile]         = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<VoiceResult | null>(null);
  const [uploadError, setUploadError]   = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Live call tab state ────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState<"upload" | "live">("upload");
  const [callId, setCallId]       = useState(() => `call-${Date.now().toString(36)}`);
  const [wsStatus, setWsStatus]   = useState<"idle" | "connecting" | "connected" | "ended">("idle");
  const [chunks, setChunks]       = useState<LiveChunk[]>([]);
  const [latestSpec, setLatestSpec] = useState<string | null>(null);
  const [latestSpecChunk, setLatestSpecChunk] = useState<number | undefined>();
  const wsRef = useRef<WebSocket | null>(null);

  // ── Browser Audio Capture states ──────────────────────────────────────────
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamsRef = useRef<MediaStream[]>([]);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const sampleBufferRef = useRef<Float32Array[]>([]);
  const recordIntervalRef = useRef<any>(null);

  // ── Drag-drop ──────────────────────────────────────────────────────────────
  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }, []);

  // ── Upload & analyze ───────────────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!file) return;
    setUploading(true);
    setUploadResult(null);
    setUploadError(null);

    try {
      const fd = new FormData();
      fd.append("audio", file);
      const res = await fetch(`${API_BASE}/analyze/voice`, { method: "POST", body: fd });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setUploadResult({
        score:    data.score ?? 0,
        verdict:  data.verdict ?? "UNKNOWN",
        severity: data.severity ?? "NONE",
        reasons:  data.reasons ?? [],
        spectrogram_image: data.spectrogram_image ?? null,
        raw: data.raw,
      });
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setUploading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // LIVE CALL TAB
  // ─────────────────────────────────────────────────────────────────────────────
  const [fullTranscript, setFullTranscript] = useState("");

  const connectWs = (captureAudio: boolean = false) => {
    const id = `call-${Date.now().toString(36)}`;
    setCallId(id);
    setChunks([]);
    setFullTranscript("");
    setLatestSpec(null);
    setWsStatus("connecting");
    setCaptureError(null);
    setIsCapturing(captureAudio);

    const ws = new WebSocket(`${WS_BASE}/ws/live-call/${id}`);
    wsRef.current = ws;

    ws.onopen  = async () => {
      setWsStatus("connected");
      if (captureAudio) {
        try {
          await startAudioCapture(ws);
        } catch (err: any) {
          console.error("Audio capture failed:", err);
          setCaptureError(err.message || "Failed to start audio capture");
          disconnectWs();
        }
      }
    };
    
    ws.onerror = () => {
      setWsStatus("ended");
      cleanupCapture();
    };
    
    ws.onclose = () => {
      setWsStatus("ended");
      cleanupCapture();
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "chunk_result") {
          const chunk: LiveChunk = {
            chunk_count:           msg.chunk_count ?? 0,
            current_score:         msg.current_score ?? 0,
            verdict:               msg.verdict ?? "SAFE",
            elapsed_seconds:       msg.elapsed_seconds ?? 0,
            high_risk_triggered:   msg.high_risk_triggered ?? false,
            time_to_alert_seconds: msg.time_to_alert_seconds,
            spectrogram_image:     msg.spectrogram_image ?? null,
            reasons:               msg.reasons ?? [],
          };
          setChunks((prev) => [...prev.slice(-19), chunk]);   // keep last 20
          
          if (msg.current_chunk_transcript) {
            setFullTranscript(prev => (prev + " " + msg.current_chunk_transcript).trim());
          }

          if (chunk.spectrogram_image) {
            setLatestSpec(chunk.spectrogram_image);
            setLatestSpecChunk(chunk.chunk_count);
          }
        }
      } catch (err) {
        console.error("WS error:", err);
      }
    };
  };

  const startAudioCapture = async (ws: WebSocket) => {
    let micStream: MediaStream | null = null;
    let tabStream: MediaStream | null = null;

    // 1. Capture user microphone (resilient fallback if denied)
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamsRef.current.push(micStream);
    } catch (e) {
      console.warn("Microphone access denied or unavailable, proceeding with tab audio only.", e);
    }

    // 2. Capture tab/system audio (required for WhatsApp call audio)
    try {
      tabStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: true
      });
      mediaStreamsRef.current.push(tabStream);
    } catch (e) {
      if (micStream) {
        micStream.getTracks().forEach(t => t.stop());
      }
      throw new Error("Display media (tab/screen sharing) permission is required to analyze the call.");
    }

    const tabAudioTracks = tabStream.getAudioTracks();
    if (tabAudioTracks.length === 0) {
      setCaptureError("Warning: No audio track detected from the shared tab. Ensure you select 'Share tab audio' when sharing WhatsApp Web!");
    }

    // 3. Initialize AudioContext at 16kHz
    const AudioCtxClass = window.AudioContext || (window as any).webkitAudioContext;
    const audioCtx = new AudioCtxClass({ sampleRate: 16000 });
    audioContextRef.current = audioCtx;

    // 4. Create ScriptProcessorNode for sample accumulation (2 inputs, 2 outputs)
    const bufferSize = 4096;
    const processor = audioCtx.createScriptProcessor(bufferSize, 2, 2);
    scriptProcessorRef.current = processor;

    const merger = audioCtx.createChannelMerger(2);

    // Route mic into Left channel (if available)
    if (micStream && micStream.getAudioTracks().length > 0) {
      const micSource = audioCtx.createMediaStreamSource(micStream);
      micSource.connect(merger, 0, 0);
    }

    // Route tab audio into Right channel (if available)
    if (tabAudioTracks.length > 0) {
      const tabSource = audioCtx.createMediaStreamSource(new MediaStream(tabAudioTracks));
      tabSource.connect(merger, 0, 1);
    }

    merger.connect(processor);

    // Connect processor to destination via a silence gain node to trigger audio events
    const silenceGain = audioCtx.createGain();
    silenceGain.gain.value = 0;
    processor.connect(silenceGain);
    silenceGain.connect(audioCtx.destination);

    // 5. Accumulate stereo samples (interleaved)
    sampleBufferRef.current = [];
    processor.onaudioprocess = (event) => {
      const left  = event.inputBuffer.getChannelData(0);
      const right = event.inputBuffer.getChannelData(1);
      
      const interleaved = new Float32Array(left.length + right.length);
      for (let i = 0; i < left.length; i++) {
        interleaved[i * 2]     = left[i];
        interleaved[i * 2 + 1] = right[i];
      }
      sampleBufferRef.current.push(interleaved);
    };

    // 6. Every 5 seconds, package samples as a 16-bit 16kHz STEREO WAV and send
    recordIntervalRef.current = setInterval(() => {
      const buffers = sampleBufferRef.current;
      if (buffers.length === 0) return;

      // Clear buffer for next chunk
      sampleBufferRef.current = [];

      const wavBuffer = encodeWAV(buffers, 16000, 2);
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(wavBuffer);
      }
    }, 5000);
  };

  const cleanupCapture = () => {
    if (recordIntervalRef.current) {
      clearInterval(recordIntervalRef.current);
      recordIntervalRef.current = null;
    }
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    mediaStreamsRef.current.forEach(stream => {
      stream.getTracks().forEach(track => track.stop());
    });
    mediaStreamsRef.current = [];
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    sampleBufferRef.current = [];
    setIsCapturing(false);
  };

  const disconnectWs = () => {
    wsRef.current?.send("END");
    wsRef.current?.close();
    setWsStatus("ended");
    cleanupCapture();
  };

  // cleanup on unmount
  useEffect(() => () => {
    wsRef.current?.close();
    if (recordIntervalRef.current) clearInterval(recordIntervalRef.current);
    mediaStreamsRef.current.forEach(stream => {
      stream.getTracks().forEach(track => track.stop());
    });
  }, []);

  const latestChunk = chunks[chunks.length - 1];

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-background text-on-background pt-24 pb-16 px-6">
      <div className="max-w-5xl mx-auto space-y-10">

        {/* ── Page header ─────────────────────────────────────────────── */}
        <div className="text-center space-y-3">
          <p className="text-primary font-headline font-bold uppercase tracking-[0.3em] text-[10px]">
            Spectral Forensics
          </p>
          <h1 className="text-4xl md:text-5xl font-headline font-bold text-white tracking-tight">
            Voice <span className="text-primary italic">Deepfake</span> Detector
          </h1>
          <p className="text-on-surface-variant font-light text-base max-w-xl mx-auto">
            Upload an audio file or connect a live WebSocket call to run acoustic
            + spectral + NLP analysis and see the mel-spectrogram fingerprint.
          </p>
        </div>

        {/* ── Tab switcher ────────────────────────────────────────────── */}
        <div className="flex justify-center gap-2">
          {(["upload", "live"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-6 py-2.5 rounded-xl text-xs font-headline font-bold uppercase tracking-widest transition-all ${
                activeTab === tab
                  ? "bg-primary text-black shadow-lg shadow-primary/20"
                  : "border border-outline/20 text-on-surface-variant hover:border-primary/30 hover:text-white"
              }`}
            >
              {tab === "upload" ? "Upload File" : "Live Call"}
            </button>
          ))}
        </div>

        {/* ─────────────────────────────────────────────────────────────── */}
        {/* UPLOAD TAB                                                      */}
        {/* ─────────────────────────────────────────────────────────────── */}
        <AnimatePresence mode="wait">
          {activeTab === "upload" && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="space-y-6"
            >
              {/* Drop zone */}
              <div
                onDrop={onDrop}
                onDragOver={(e) => e.preventDefault()}
                className="glass-panel rounded-2xl border-2 border-dashed border-outline/20 hover:border-primary/30 transition-colors p-10 text-center cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*"
                  className="hidden"
                  onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
                />
                <Upload className="w-10 h-10 text-primary/40 mx-auto mb-3" />
                {file ? (
                  <p className="text-white font-medium">{file.name}</p>
                ) : (
                  <p className="text-on-surface-variant font-light text-sm">
                    Drop a WAV / MP3 / OGG file here, or click to browse
                  </p>
                )}
              </div>

              <div className="flex justify-center">
                <motion.button
                  disabled={!file || uploading}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleAnalyze}
                  className="bg-primary text-black font-headline font-bold px-12 py-4 rounded-2xl shadow-lg shadow-primary/20 hover:bg-primary-dark transition-all disabled:opacity-40 flex items-center gap-3"
                >
                  {uploading ? <><Loader2 className="w-5 h-5 animate-spin" /> Analyzing…</> : <><Shield className="w-5 h-5" /> Run Analysis</>}
                </motion.button>
              </div>

              {uploadError && (
                <p className="text-center text-error text-sm">{uploadError}</p>
              )}

              {/* Results */}
              <AnimatePresence>
                {uploadResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    className="grid md:grid-cols-2 gap-6"
                  >
                    {/* Left: score + verdict */}
                    <div className={`glass-panel rounded-2xl border-l-4 ${scoreBorder(uploadResult.score)} p-6 space-y-5`}>
                      <div className="flex items-center gap-4">
                        <ScoreDial score={uploadResult.score} />
                        <div>
                          <p className={`text-2xl font-headline font-bold ${scoreColor(uploadResult.score)}`}>
                            {uploadResult.verdict}
                          </p>
                          <p className="text-xs text-on-surface-variant">{uploadResult.severity} severity</p>
                          {uploadResult.raw?.is_deepfake && (
                            <span className="mt-2 inline-block text-[9px] font-bold bg-error/10 text-error border border-error/30 px-2 py-0.5 rounded-full uppercase tracking-widest">
                              Deepfake Detected
                            </span>
                          )}
                        </div>
                      </div>

                      {uploadResult.raw && (
                        <div className="grid grid-cols-3 gap-2 text-center">
                          {[
                            { label: "Acoustic", val: uploadResult.raw.acoustic_score },
                            { label: "NLP",      val: uploadResult.raw.nlp_score },
                            { label: "Deepfake", val: uploadResult.raw.deepfake_score },
                          ].map(({ label, val }) => (
                            <div key={label} className="bg-surface/40 rounded-xl p-2">
                              <p className="text-[9px] text-on-surface-variant uppercase tracking-widest">{label}</p>
                              <p className="text-base font-headline font-bold text-white">{val?.toFixed(0) ?? "–"}</p>
                            </div>
                          ))}
                        </div>
                      )}

                      {uploadResult.raw?.transcript && (
                        <div className="bg-surface/30 rounded-xl p-3">
                          <p className="text-[9px] uppercase tracking-widest text-on-surface-variant mb-1">Transcript</p>
                          <p className="text-[11px] text-on-surface-variant font-light leading-relaxed line-clamp-3">
                            {uploadResult.raw.transcript}
                          </p>
                        </div>
                      )}

                      <div>
                        <p className="text-[9px] uppercase tracking-widest text-on-surface-variant mb-2">Detection Reasons</p>
                        <ReasonList reasons={uploadResult.reasons} />
                      </div>
                    </div>

                    {/* Right: spectrogram */}
                    <SpectrogramPanel
                      src={uploadResult.spectrogram_image}
                      label="Audio Spectrogram Analysis"
                      live={false}
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}

          {/* ─────────────────────────────────────────────────────────────── */}
          {/* LIVE CALL TAB                                                   */}
          {/* ─────────────────────────────────────────────────────────────── */}
          {activeTab === "live" && (
            <motion.div
              key="live"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              className="space-y-6"
            >
              {/* Connection controls */}
              <div className="glass-panel rounded-2xl p-6 space-y-4">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="flex-1 space-y-1">
                    <p className="text-xs text-on-surface-variant font-light">WebSocket Session ID</p>
                    <p className="font-mono text-sm text-primary">{callId}</p>
                  </div>
                  
                  <div className="flex flex-wrap gap-3">
                    {wsStatus !== "connected" && wsStatus !== "connecting" ? (
                      <>
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => connectWs(true)}
                          className="flex items-center gap-2 bg-primary text-black font-headline font-bold px-6 py-3 rounded-xl text-xs shadow-lg shadow-primary/20"
                        >
                          <Mic className="w-4 h-4" /> Connect & Capture Web Call
                        </motion.button>
                        
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => connectWs(false)}
                          className="flex items-center gap-2 border border-outline/30 text-white font-headline font-bold px-6 py-3 rounded-xl text-xs hover:bg-white/5"
                        >
                          <Radio className="w-4 h-4" /> Monitor Stream Only
                        </motion.button>
                      </>
                    ) : (
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={disconnectWs}
                        className="flex items-center gap-2 bg-error/80 text-black font-headline font-bold px-6 py-3 rounded-xl text-xs"
                      >
                        <MicOff className="w-4 h-4" /> End Call
                      </motion.button>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 shrink-0">
                    <div className={`w-2 h-2 rounded-full ${
                      wsStatus === "connected" ? "bg-primary animate-pulse" :
                      wsStatus === "connecting" ? "bg-yellow-400 animate-pulse" : "bg-outline"
                    }`} />
                    <span className="text-[10px] font-headline font-bold text-on-surface-variant uppercase tracking-widest">
                      {wsStatus}
                    </span>
                  </div>
                </div>

                {/* Instructions & Capture warnings */}
                {wsStatus !== "connected" && wsStatus !== "connecting" && (
                  <div className="bg-surface/30 rounded-xl p-4 border border-outline/10 text-xs text-on-surface-variant space-y-2">
                    <p className="font-semibold text-white flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 text-primary" /> How to scan WhatsApp Web / Google Meet / Web Calls:
                    </p>
                    <ul className="list-disc pl-4 space-y-1 font-light">
                      <li>Click <strong>Connect & Capture Web Call</strong>.</li>
                      <li>Allow browser microphone access when prompted (captures your voice).</li>
                      <li>In the browser tab sharing dialog, select the <strong>WhatsApp Web tab</strong> (or system screen) and <strong>MUST check the &quot;Share tab audio&quot; / &quot;Share system audio&quot; option</strong> (captures caller&apos;s voice).</li>
                    </ul>
                  </div>
                )}

                {captureError && (
                  <div className="bg-error/10 border border-error/20 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-error font-light">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{captureError}</span>
                  </div>
                )}
              </div>

              {/* Live grid: spectrogram left, score + chunks right */}
              {chunks.length > 0 && latestChunk && (
                <div className="grid md:grid-cols-2 gap-6">
                  {/* Spectrogram — updates every 3rd chunk */}
                  <SpectrogramPanel
                    src={latestSpec}
                    label="Live Spectrogram"
                    live={wsStatus === "connected"}
                    chunkNumber={latestSpecChunk}
                  />

                  {/* Score panel */}
                  <div className="glass-panel rounded-2xl border border-outline/10 p-6 space-y-5">
                    <div className="flex items-center justify-between">
                      <ScoreDial score={Math.round(latestChunk.current_score)} />
                      <div className="space-y-2 text-right">
                        <p className={`text-2xl font-headline font-bold ${scoreColor(latestChunk.current_score)}`}>
                          {latestChunk.verdict}
                        </p>
                        <div className="flex items-center gap-1.5 justify-end">
                          <Clock className="w-3 h-3 text-on-surface-variant/40" />
                          <span className="text-xs text-on-surface-variant">
                            {latestChunk.elapsed_seconds.toFixed(1)}s elapsed
                          </span>
                        </div>
                        {latestChunk.high_risk_triggered && (
                          <div className="flex items-center gap-1.5 justify-end">
                            <ShieldAlert className="w-3.5 h-3.5 text-error" />
                            <span className="text-[10px] font-bold text-error">
                              FLAGGED in {latestChunk.time_to_alert_seconds?.toFixed(2)}s
                            </span>
                          </div>
                        )}
                        {!latestChunk.high_risk_triggered && (
                          <div className="flex items-center gap-1.5 justify-end">
                            <CheckCircle2 className="w-3.5 h-3.5 text-primary/50" />
                            <span className="text-[10px] text-primary/50">No high-risk flag</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Chunk history mini-bar */}
                    <div>
                      <p className="text-[9px] uppercase tracking-widest text-on-surface-variant mb-2">
                        Score history (last {chunks.length} chunks)
                      </p>
                      <div className="flex items-end gap-0.5 h-10">
                        {chunks.map((c, i) => {
                          const h = Math.max(4, (c.current_score / 100) * 40);
                          return (
                            <div
                              key={i}
                              className={`flex-1 rounded-sm transition-all ${
                                c.current_score >= 70 ? "bg-error" :
                                c.current_score >= 55 ? "bg-orange-400" : "bg-primary/60"
                              }`}
                              style={{ height: `${h}px` }}
                            />
                          );
                        })}
                      </div>
                    </div>

                    <div>
                      <p className="text-[9px] uppercase tracking-widest text-on-surface-variant mb-2">
                        Latest reasons
                      </p>
                      <ReasonList reasons={latestChunk.reasons} />
                    </div>
                  </div>
                </div>
              )}

              {wsStatus === "connected" && chunks.length === 0 && (
                <div className="flex flex-col items-center gap-3 py-16 border-2 border-dashed border-outline/10 rounded-3xl">
                  <Radio className="w-10 h-10 text-primary/30 animate-pulse" />
                  <p className="text-on-surface-variant/40 text-sm font-light text-center px-4">
                    {isCapturing
                      ? "Actively capturing and streaming Web Call audio to scanner..."
                      : "Listening passively... Send audio chunks over the WebSocket to analyze."
                    }
                  </p>
                  <p className="text-[10px] font-mono text-on-surface-variant/20">
                    ws://localhost:8000/ws/live-call/{callId}
                  </p>
                </div>
              )}

              {wsStatus === "idle" && (
                <div className="flex flex-col items-center gap-3 py-16 border-2 border-dashed border-outline/10 rounded-3xl">
                  <AlertTriangle className="w-10 h-10 text-on-surface-variant/20" />
                  <p className="text-on-surface-variant/40 text-sm font-light">
                    Click Connect to open a live analysis WebSocket session
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
