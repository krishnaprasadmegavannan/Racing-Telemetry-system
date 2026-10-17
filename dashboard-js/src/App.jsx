// src/App.jsx
import React, { useState } from 'react';
import { useTelemetry } from './useTelemetry';
import F1TelemetryClient from './pages/F1TelemetryClient';
import Cockpit from './pages/Cockpit';
import Powertrain from './pages/Powertrain';
import Diagnostics from './pages/Diagnostics';
import { Zap, Gauge, Radio, Cpu, Layers } from 'lucide-react';

export default function App() {
  const { data, history, stats, alerts, isConnected, isStale, setAlerts, lapTiming } = useTelemetry(null);
  const [currentPage, setCurrentPage] = useState('F1_TELEMETRY');

  const handleDismissAlert = (id) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id));
  };

  if (!data) return (
    <div className="min-h-screen bg-[#0a0d14] flex flex-col items-center justify-center font-mono text-cyan-400 gap-4">
      <div className="relative">
        <div className="animate-spin rounded-full h-14 w-14 border-t-2 border-b-2 border-emerald-400" />
        <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-white">50Hz</div>
      </div>
      <div className="text-xs tracking-widest uppercase animate-pulse text-emerald-400">
        CONNECTING TO RACING TELEMETRY PIT-WALL...
      </div>
      <div className="text-[10px] text-slate-500">
        Streaming FastF1 Monza telemetry...
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#0a0d14] text-white font-sans flex flex-col">
      
      {/* HEADER */}
      <header className="border-b border-[#232736] bg-[#0e111a]/95 px-6 py-3.5 flex flex-wrap justify-between items-center z-40 shrink-0 sticky top-0 backdrop-blur-md">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-500/10 border border-red-500/20 rounded-xl">
              <Zap className="text-red-500 animate-pulse" size={20} />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-widest text-white m-0 leading-none">
                RACING TELEMETRY <span className="text-red-500 text-xs font-mono">| PIT-WALL</span>
              </h1>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                {data?.transmission_information?.includes('ESP32')
                  ? `HARDWARE LINK // ${data.transmission_information} (DUAL ESP32)`
                  : 'HOTLAP QUALIFYING // FASTF1 MONZA (12KG FUEL, SOFT C4)'}
              </span>
            </div>
          </div>

          <nav className="flex gap-1.5 bg-[#141824] p-1.5 rounded-xl border border-[#232736] font-mono text-xs">
            {[
              { id: 'F1_TELEMETRY', label: 'F1 TELEMETRY CLIENT', icon: Gauge },
              { id: 'COCKPIT', label: 'COCKPIT HUD', icon: Layers },
              { id: 'POWERTRAIN', label: 'POWERTRAIN & DYNAMICS', icon: Radio },
              { id: 'DIAGNOSTICS', label: 'SCHEMA & ESP32 INSPECTOR', icon: Cpu },
            ].map(({ id, label, icon: Icon }) => (
              <button 
                key={id}
                onClick={() => setCurrentPage(id)}
                className={`px-3.5 py-1.5 rounded-lg font-bold flex items-center gap-2 transition-all ${
                  currentPage === id 
                    ? 'bg-emerald-500 text-black shadow-lg shadow-emerald-500/20' 
                    : 'text-slate-400 hover:text-white hover:bg-[#1e2334]'
                }`}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <div className={`w-[210px] flex items-center justify-center gap-2 px-3.5 py-1.5 rounded-full border text-[10px] font-mono font-bold transition-all duration-300 ${
            isConnected && !isStale 
              ? data?.transmission_information?.includes('ESP32')
                ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-400"
                : "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
              : "bg-red-500/10 border-red-500/30 text-red-500"
          }`}>
            <span className={`w-2 h-2 rounded-full shrink-0 ${
              isConnected && !isStale 
                ? data?.transmission_information?.includes('ESP32')
                  ? "bg-cyan-400 animate-ping"
                  : "bg-emerald-400 animate-ping" 
                : "bg-red-500"
            }`} />
            <span className="truncate">
              {isConnected && !isStale 
                ? (data?.transmission_information?.includes('ESP32') ? "ESP32 HARDWARE LIVE" : "FASTF1 50Hz STREAM")
                : "DISCONNECTED / HELD"}
            </span>
          </div>
        </div>
      </header>

      <main className="flex-grow p-4 md:p-6 overflow-y-auto">
        {currentPage === 'F1_TELEMETRY' && (
          <F1TelemetryClient data={data} history={history} stats={stats} lapTiming={lapTiming} />
        )}

        {currentPage === 'COCKPIT' && (
          <Cockpit data={data} alerts={alerts} onDismissAlert={handleDismissAlert} lapTiming={lapTiming} />
        )}
        
        {currentPage === 'POWERTRAIN' && (
          <Powertrain data={data} />
        )}

        {currentPage === 'DIAGNOSTICS' && (
          <Diagnostics data={data} />
        )}
      </main>
    </div>
  );
}