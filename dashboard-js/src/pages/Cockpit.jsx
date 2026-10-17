// src/pages/Cockpit.jsx
import React from 'react';
import SuperbikeCluster from '../components/SuperbikeCluster';
import MonzaMap from '../components/MonzaMap';
import AlertsPanel from '../components/AlertsPanel';
import { Clock, Navigation, Flag, Trophy, Timer, Activity } from 'lucide-react';

export default function Cockpit({ data, alerts, onDismissAlert, lapTiming }) {
  const currentLap = lapTiming?.currentLap || data?.tyre_age_lap || 2;
  const activeSector = lapTiming?.activeSector || 1;
  const currentSectorSec = ((lapTiming?.currentSectorMs || 0) / 1000).toFixed(3);
  const lapHistory = lapTiming?.lapHistory || [];

  return (
    <div className="grid grid-cols-12 gap-4 w-full max-w-[1920px] mx-auto font-mono text-slate-200 items-start">
      
      {/* LEFT COLUMN: Telemetry Cluster & Timing */}
      <div className="col-span-12 lg:col-span-4 flex flex-col gap-4">
        <SuperbikeCluster 
          rpm={data?.rpm || 0} 
          speed={data?.speed || 0} 
          throttle={data?.throttle || 0} 
          brake={data?.brake_pressure || 0} 
          gear={data?.gear || 1}
        />

        {/* ── CARD 1: LIVE RUNNING LAP & DYNAMIC SECTORS ────────────────────── */}
        <div className="bg-[#12151e] p-4 rounded-xl border border-[#232736] shadow-sm flex flex-col gap-3">
          <div className="flex justify-between items-center border-b border-[#1f2536] pb-2">
            <span className="text-xs text-slate-400 font-bold flex items-center gap-2">
              <Clock size={15} className="text-emerald-400 animate-pulse" /> CURRENT LAP STATUS
            </span>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider bg-red-500/15 text-red-400 border-red-500/30">
                HOTLAP QUALI
              </span>
              <span className="flex items-center gap-1.5 text-[11px] text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded font-bold border border-emerald-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                LAP {currentLap} / 53
              </span>
            </div>
          </div>

          {/* Running Lap Clock */}
          <div className="flex flex-col items-center justify-center py-2 bg-[#0d1017] rounded-lg border border-[#1d2232]">
            <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold mb-0.5">
              LIVE LAP TIMER
            </span>
            <div className="text-4xl font-black text-white tracking-wider my-0.5 font-mono drop-shadow">
              {lapTiming?.currentLapFormatted || '0:00.000'}
            </div>
            <div className="mt-1 flex flex-wrap items-center justify-center gap-2">
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider ${
                activeSector === 1 
                  ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                  : activeSector === 2
                    ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                    : 'bg-purple-500/10 text-purple-400 border-purple-500/30'
              }`}>
                SECTOR {activeSector} ACTIVE
              </span>
              <span className="text-[10px] text-slate-500">
                DRS: <strong className={data?.drs ? "text-emerald-400" : "text-slate-400"}>{data?.drs ? "OPEN" : "CLOSED"}</strong>
              </span>
              <span className="text-[10px] text-slate-400 border-l border-slate-700 pl-2">
                FUEL: <strong className="text-amber-400 font-mono">{data?.fuel_kg !== undefined ? `${data.fuel_kg} kg` : (lapTiming?.fuelKg ? `${lapTiming.fuelKg} kg` : '12.0 kg')}</strong>
              </span>
              <span className="text-[10px] text-slate-400 border-l border-slate-700 pl-2">
                TYRE: <strong className="text-cyan-400 font-mono">{data?.tyre_compound || lapTiming?.compound || 'SOFT (C4)'}</strong>
              </span>
            </div>
          </div>

          {/* Dynamic Sectors */}
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            {/* SECTOR 1 */}
            <div className={`p-2.5 rounded-lg border transition-all ${
              activeSector === 1 
                ? 'bg-[#121c2a] border-cyan-500/50 shadow-sm shadow-cyan-500/10' 
                : 'bg-[#181c29] border-[#262c3e]'
            }`}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-slate-400 font-bold">SECTOR 1</span>
                {activeSector === 1 ? (
                  <span className="text-[9px] text-cyan-400 bg-cyan-500/20 px-1 py-0.2 rounded font-bold animate-pulse">LIVE</span>
                ) : (
                  <span className="text-[9px] text-emerald-400 bg-emerald-500/10 px-1 py-0.2 rounded font-bold">DONE</span>
                )}
              </div>
              <span className={`text-sm font-black font-mono block ${
                activeSector === 1 ? 'text-cyan-400 animate-pulse' : 'text-emerald-400'
              }`}>
                {activeSector === 1 
                  ? `${currentSectorSec}s`
                  : lapTiming?.sector1Ms 
                    ? `${(lapTiming.sector1Ms / 1000).toFixed(3)}s` 
                    : (lapTiming?.fastestSector1Formatted || '27.412s')}
              </span>
              <span className="text-[9px] text-slate-500 block mt-0.5">
                Target: {lapTiming?.fastestSector1Formatted || '27.412s'}
              </span>
            </div>

            {/* SECTOR 2 */}
            <div className={`p-2.5 rounded-lg border transition-all ${
              activeSector === 2 
                ? 'bg-[#221c15] border-amber-500/50 shadow-sm shadow-amber-500/10' 
                : 'bg-[#181c29] border-[#262c3e]'
            }`}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-slate-400 font-bold">SECTOR 2</span>
                {activeSector === 2 ? (
                  <span className="text-[9px] text-amber-400 bg-amber-500/20 px-1 py-0.2 rounded font-bold animate-pulse">LIVE</span>
                ) : activeSector > 2 ? (
                  <span className="text-[9px] text-purple-400 bg-purple-500/10 px-1 py-0.2 rounded font-bold">DONE</span>
                ) : (
                  <span className="text-[9px] text-slate-500 bg-slate-800 px-1 py-0.2 rounded">WAIT</span>
                )}
              </div>
              <span className={`text-sm font-black font-mono block ${
                activeSector === 2 
                  ? 'text-amber-400 animate-pulse' 
                  : activeSector > 2 
                    ? 'text-purple-400' 
                    : 'text-slate-500'
              }`}>
                {activeSector === 2 
                  ? `${currentSectorSec}s`
                  : activeSector > 2
                    ? (lapTiming?.sector2Ms ? `${(lapTiming.sector2Ms / 1000).toFixed(3)}s` : (lapTiming?.fastestSector2Formatted || '37.224s'))
                    : '--.---s'}
              </span>
              <span className="text-[9px] text-slate-500 block mt-0.5">
                Target: {lapTiming?.fastestSector2Formatted || '37.224s'}
              </span>
            </div>

            {/* SECTOR 3 */}
            <div className={`p-2.5 rounded-lg border transition-all ${
              activeSector === 3 
                ? 'bg-[#221226] border-purple-500/50 shadow-sm shadow-purple-500/10' 
                : 'bg-[#181c29] border-[#262c3e]'
            }`}>
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] text-slate-400 font-bold">SECTOR 3</span>
                {activeSector === 3 ? (
                  <span className="text-[9px] text-purple-400 bg-purple-500/20 px-1 py-0.2 rounded font-bold animate-pulse">LIVE</span>
                ) : (
                  <span className="text-[9px] text-slate-500 bg-slate-800 px-1 py-0.2 rounded">WAIT</span>
                )}
              </div>
              <span className={`text-sm font-black font-mono block ${
                activeSector === 3 ? 'text-purple-400 animate-pulse' : 'text-slate-500'
              }`}>
                {activeSector === 3 ? `${currentSectorSec}s` : '--.---s'}
              </span>
              <span className="text-[9px] text-slate-500 block mt-0.5">
                Target: {lapTiming?.fastestSector3Formatted || '15.525s'}
              </span>
            </div>
          </div>
        </div>

        {/* ── CARD 2: SESSION FASTEST LAP (BENCHMARK & RECORD) ────────────── */}
        <div className="bg-[#141220] p-4 rounded-xl border border-purple-500/30 shadow-sm flex flex-col gap-2 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-purple-500/5 rounded-full blur-2xl pointer-events-none" />

          <div className="flex justify-between items-center">
            <span className="text-xs text-purple-300 font-bold flex items-center gap-2">
              <Trophy size={14} className="text-purple-400" /> SESSION FASTEST LAP
            </span>
            <span className="text-[10px] text-purple-300 bg-purple-500/20 px-2 py-0.5 rounded font-bold border border-purple-500/40 tracking-wider">
              PURPLE BENCHMARK
            </span>
          </div>

          <div className="flex items-baseline justify-between my-1">
            <div className="text-3xl font-black text-white font-mono tracking-tight flex items-baseline gap-2">
              <span className="text-purple-400">{lapTiming?.fastestLapFormatted || '1:20.161'}</span>
            </div>
            <div className="text-right">
              <span className="text-[11px] text-slate-400 block font-bold">
                LAP {lapTiming?.fastestLapNumber || 1}
              </span>
              <span className="text-[10px] text-purple-400">
                {lapTiming?.fastestDriver || 'Charles Leclerc (Q3 Pole)'}
              </span>
            </div>
          </div>

          {/* Fastest Sectors Breakdown */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-purple-500/20 text-center text-[11px]">
            <div className="bg-[#19152b] py-1 px-1.5 rounded border border-purple-500/20">
              <span className="text-[9px] text-slate-400 block">S1 BEST</span>
              <span className="font-bold text-purple-300">{lapTiming?.fastestSector1Formatted || '27.412s'}</span>
            </div>
            <div className="bg-[#19152b] py-1 px-1.5 rounded border border-purple-500/20">
              <span className="text-[9px] text-slate-400 block">S2 BEST</span>
              <span className="font-bold text-purple-300">{lapTiming?.fastestSector2Formatted || '37.224s'}</span>
            </div>
            <div className="bg-[#19152b] py-1 px-1.5 rounded border border-purple-500/20">
              <span className="text-[9px] text-slate-400 block">S3 BEST</span>
              <span className="font-bold text-purple-300">{lapTiming?.fastestSector3Formatted || '15.525s'}</span>
            </div>
          </div>
        </div>

        {/* ── CARD 3: LAST COMPLETED LAP & DELTA ───────────────────────────── */}
        {lapTiming?.lastLapFormatted && lapTiming.lastLapFormatted !== '--:--.---' && (
          <div className="bg-[#12151e] px-4 py-2.5 rounded-xl border border-[#232736] flex justify-between items-center text-xs">
            <span className="text-slate-400 flex items-center gap-1.5 font-bold">
              <Timer size={14} className="text-cyan-400" /> LAST COMPLETED LAP:
            </span>
            <div className="flex items-center gap-3">
              <span className="font-black text-white font-mono text-sm">{lapTiming.lastLapFormatted}</span>
              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border font-mono ${
                lapTiming.lastLapDelta === 'PURPLE'
                  ? 'bg-purple-500/20 text-purple-400 border-purple-500/40'
                  : lapTiming.lastLapDelta.startsWith('-')
                    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                    : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
              }`}>
                {lapTiming.lastLapDelta}
              </span>
            </div>
          </div>
        )}

        {/* ── CARD 4: COMPLETED LAPS HISTORY TABLE ─────────────────────────── */}
        {lapHistory.length > 0 && (
          <div className="bg-[#12151e] p-3 rounded-xl border border-[#232736] flex flex-col gap-2">
            <div className="flex justify-between items-center text-xs text-slate-400 font-bold border-b border-[#1f2536] pb-1.5">
              <span className="flex items-center gap-1.5">
                <Flag size={13} className="text-red-500" /> LAP HISTORY LOG
              </span>
              <span className="text-[10px] text-slate-500">{lapHistory.length} COMPLETED</span>
            </div>

            <div className="max-h-40 overflow-y-auto space-y-1 pr-1 font-mono text-[11px]">
              <div className="grid grid-cols-6 text-[9px] text-slate-500 font-bold uppercase pb-1 px-1">
                <span>LAP</span>
                <span className="col-span-2">TIME</span>
                <span>DELTA</span>
                <span>S1</span>
                <span>S2</span>
              </div>
              {lapHistory.map((item, idx) => (
                <div 
                  key={idx} 
                  className={`grid grid-cols-6 items-center px-1.5 py-1 rounded border text-[11px] ${
                    item.isPurple 
                      ? 'bg-purple-950/20 border-purple-500/40 text-purple-200' 
                      : 'bg-[#181c29] border-[#232838] text-slate-300'
                  }`}
                >
                  <span className="font-bold flex items-center gap-1">
                    #{item.lap}
                    {item.isPurple && <span className="text-[8px] bg-purple-500/40 text-purple-200 px-1 rounded">PB</span>}
                  </span>
                  <span className="col-span-2 font-bold font-mono">{item.formatted}</span>
                  <span className={`text-[10px] font-bold ${
                    item.isPurple 
                      ? 'text-purple-400' 
                      : item.delta?.startsWith('-') 
                        ? 'text-emerald-400' 
                        : 'text-amber-400'
                  }`}>
                    {item.delta}
                  </span>
                  <span className="text-slate-400 text-[10px]">{item.s1Formatted}</span>
                  <span className="text-slate-400 text-[10px]">{item.s2Formatted}</span>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* CENTER COLUMN: Track Positioning */}
      <div className="col-span-12 lg:col-span-5 flex flex-col">
        <MonzaMap 
          track_x={data?.track_x} 
          track_y={data?.track_y} 
          speed={data?.speed || 0} 
          brake={data?.brake_pressure || 0} 
          throttle={data?.throttle || 0}
          gear={data?.gear || 1}
          cornerName={data?.corner_name}
          sector={data?.sector || activeSector}
          lat={data?.latitude}
          lon={data?.longitude}
        />
      </div>

      {/* RIGHT COLUMN: Alerts Panel */}
      <div className="col-span-12 lg:col-span-3 flex flex-col">
        <AlertsPanel alerts={alerts} onDismiss={onDismissAlert} />
      </div>

    </div>
  );
}