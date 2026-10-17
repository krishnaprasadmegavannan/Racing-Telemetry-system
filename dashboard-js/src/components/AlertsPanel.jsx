// src/components/AlertsPanel.jsx
import React, { useState } from 'react';
import {
  ShieldAlert,
  AlertOctagon,
  CheckCircle2,
  X,
  ChevronDown,
  ChevronUp,
  Info,
} from 'lucide-react';

export default function AlertsPanel({
  alerts = [],
  onDismiss,
}) {
  const [isMinimized, setIsMinimized] = useState(false);

  const handleDismiss = (id) => {
    if (typeof onDismiss === 'function') {
      onDismiss(id);
    }
  };

  // Only take the single active alert (strictly ONE warning at a time)
  const activeAlert = alerts && alerts.length > 0 ? alerts[0] : null;

  return (
    <div
      className="flex flex-col bg-[#12151e] rounded-xl border border-[#232736] shadow-sm font-mono overflow-hidden"
    >
      {/* HEADER */}
      <div
        className="flex justify-between items-center p-3.5 border-b border-[#232736] cursor-pointer hover:bg-[#181c29]/50 transition-colors"
        onClick={() => setIsMinimized(!isMinimized)}
      >
        <span className="text-xs font-bold text-slate-200 flex items-center gap-2">
          <ShieldAlert
            size={16}
            className={activeAlert ? "text-amber-400 animate-pulse" : "text-emerald-400"}
          />
          SYSTEM ALERTS & NOTICES
        </span>

        <div className="flex items-center gap-2.5">
          <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold border ${
            activeAlert 
              ? activeAlert.level === 'critical' || activeAlert.level === 'warning'
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                : 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
          }`}>
            {activeAlert ? '1 ACTIVE' : 'NOMINAL'}
          </span>

          {isMinimized ? (
            <ChevronDown size={16} className="text-slate-400" />
          ) : (
            <ChevronUp size={16} className="text-slate-400" />
          )}
        </div>
      </div>

      {/* SINGLE ACTIVE ALERT OR NOMINAL STATE */}
      {!isMinimized && (
        <div className="p-3.5 flex flex-col justify-center">
          {!activeAlert ? (
            /* ALL SYSTEMS NOMINAL */
            <div className="text-slate-400 text-xs text-center py-6 px-3 bg-[#161a26] rounded-xl border border-[#242b3e] flex flex-col items-center justify-center gap-2">
              <div className="p-2.5 bg-emerald-500/10 rounded-full border border-emerald-500/20">
                <CheckCircle2
                  size={20}
                  className="text-emerald-400"
                />
              </div>
              <span className="font-bold text-slate-200 text-xs tracking-wider">
                ALL SYSTEMS NOMINAL
              </span>
              <span className="text-[10px] text-slate-400">
                Engine, Brakes & Aerodynamics in Safe Operating Envelope
              </span>
            </div>
          ) : (
            /* EXACTLY ONE ACTIVE WARNING */
            <div
              className={`p-3.5 rounded-xl border text-xs flex items-start justify-between gap-3 shadow-md transition-all ${
                activeAlert.level === 'critical'
                  ? 'bg-red-950/40 border-red-800/60 text-red-200 shadow-[0_0_12px_rgba(239,68,68,0.2)]'
                  : activeAlert.level === 'warning'
                  ? 'bg-amber-950/40 border-amber-800/60 text-amber-200 shadow-[0_0_12px_rgba(245,158,11,0.2)]'
                  : 'bg-cyan-950/40 border-cyan-800/60 text-cyan-200 shadow-[0_0_12px_rgba(6,182,212,0.2)]'
              }`}
            >
              <div className="flex items-start gap-2.5">
                {activeAlert.level === 'critical' || activeAlert.level === 'warning' ? (
                  <AlertOctagon
                    size={18}
                    className={`shrink-0 mt-0.5 ${
                      activeAlert.level === 'critical' ? 'text-red-400' : 'text-amber-400'
                    }`}
                  />
                ) : (
                  <Info
                    size={18}
                    className="shrink-0 mt-0.5 text-cyan-400"
                  />
                )}

                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="font-black uppercase text-[10px] tracking-wider bg-black/40 px-1.5 py-0.5 rounded border border-white/10">
                      {activeAlert.alert_type || activeAlert.level}
                    </span>
                    <span className="text-[10px] text-slate-400">
                      {activeAlert.time}
                    </span>
                  </div>

                  <span className="text-xs leading-relaxed font-bold text-white">
                    {activeAlert.message}
                  </span>
                </div>
              </div>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDismiss(activeAlert.id);
                }}
                className="p-1 hover:bg-black/40 rounded text-slate-400 hover:text-white transition-colors shrink-0"
                title="Dismiss Alert"
                aria-label="Dismiss alert"
              >
                <X size={14} />
              </button>
            </div>
          )}

          {/* TELEMETRY BUS STATUS STRIP */}
          <div className="mt-3 pt-2.5 border-t border-[#1f2536] flex justify-between items-center text-[10px] text-slate-400">
            <span>LINK: <strong className="text-emerald-400">FASTF1 LIVE</strong></span>
            <span>ALERT FILTER: <strong className="text-cyan-400">SINGLE EVENT</strong></span>
          </div>
        </div>
      )}
    </div>
  );
}