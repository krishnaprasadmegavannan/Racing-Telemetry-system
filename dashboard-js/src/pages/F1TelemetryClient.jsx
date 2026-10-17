// src/pages/F1TelemetryClient.jsx
import React from 'react';
import F1Gauge from '../components/F1Gauge';
import {
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { Activity, Clock, Zap, Cpu, Radio, ShieldCheck } from 'lucide-react';

function formatLapMs(ms) {
  if (!ms || ms <= 0) return '1:20.161';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const milliseconds = ms % 1000;
  return `${minutes}:${String(seconds).padStart(2, '0')}.${String(milliseconds).padStart(3, '0')}`;
}

export default function F1TelemetryClient({ data, history = [], stats = {}, lapTiming, telemetryMode }) {
  const activeMode = lapTiming?.mode || telemetryMode || data?.telemetry_mode || 'HOTLAP';
  const chartData = history.map((pt, idx) => ({
    id: idx,
    time: pt.timestamp ? new Date(pt.timestamp * 1000).toLocaleTimeString().slice(3) : idx,
    speed: Math.round(pt.speed),
    rpm: Math.round(pt.rpm),
    throttle: Math.round(pt.throttle),
    brake: Math.round(pt.brake_pressure),
    powerKW: Number(pt.powerKW || 0),
    voltage: Number(pt.battery_voltage || 14.2),
  }));

  return (
    <div className="flex flex-col gap-4 w-full max-w-[1920px] mx-auto text-slate-200 font-mono pb-6 select-none">
      
      {/* ======================================================== */}
      {/* 1. TOP SUBHEADER / TAG FILTER BAR                         */}
      {/* ======================================================== */}
      <div className="flex flex-wrap justify-between items-center bg-[#10131b] border border-[#232736] px-4 py-2.5 rounded-xl text-xs gap-3">
        <div className="flex items-center gap-3">
          <span className="text-slate-400 font-bold flex items-center gap-1.5">
            <Radio size={14} className="text-red-500 animate-pulse" />
            General / F1 Telemetry Client Go
          </span>
          <div className="hidden md:flex items-center gap-2">
            <span className="bg-[#1b2030] text-cyan-400 px-2 py-0.5 rounded border border-[#2a324b] text-[10px]">
              namespace: <strong className="text-white">monza-apex</strong>
            </span>
            <span className="bg-[#1b2030] text-cyan-400 px-2 py-0.5 rounded border border-[#2a324b] text-[10px]">
              pod: <strong className="text-white">apex-01-v10</strong>
            </span>
            <span className="bg-[#1b2030] text-amber-400 px-2 py-0.5 rounded border border-[#2a324b] text-[10px]">
              interval: <strong className="text-white">50Hz</strong>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <Clock size={13} className="text-slate-500" />
            Rolling Window: <span className="text-white font-bold">150 Samples</span>
          </span>
          <span className="flex items-center gap-1.5 text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/20">
            <ShieldCheck size={13} />
            Hardware Sync: ESP32 Ready
          </span>
        </div>
      </div>

      {/* ======================================================== */}
      {/* 2. TOP GAUGES SECTION (ROWS 1 & 2 OF REFERENCE)          */}
      {/* ======================================================== */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-7 gap-3">
        
        {/* ROW 1 */}
        {/* Gauge 1: Speed Trap */}
        <F1Gauge
          title="Speed Trap"
          value={data?.speedTrap || 350.0}
          min={0}
          max={360}
          unit="km/h"
          color="multi"
          decimals={2}
        />

        {/* Gauge 2: Front Left Tyre Wear */}
        <F1Gauge
          title="Front Left Tyre Wear"
          value={data?.tyre_wear_fl || 13.0}
          min={0}
          max={100}
          unit="%"
          color="green"
          decimals={2}
        />

        {/* Gauge 3: Front Right Tyre Wear */}
        <F1Gauge
          title="Front Right Tyre Wear"
          value={data?.tyre_wear_fr || 11.0}
          min={0}
          max={100}
          unit="%"
          color="green"
          decimals={2}
        />

        {/* Card 4: Tyre Age Lap */}
        <div className="bg-[#12151e] border border-[#232736] rounded-xl p-3 flex flex-col items-center justify-between shadow-sm relative">
          <span className="text-[11px] font-mono tracking-wide text-slate-400">
            Tyre Age Lap
          </span>
          <div className="my-auto flex items-baseline justify-center gap-2">
            <span className="text-4xl font-black text-emerald-400 font-mono">
              {data?.tyre_age_lap || lapTiming?.currentLap || 1}
            </span>
            <div className="flex flex-col gap-0.5">
              <span className="w-1.5 h-3 bg-emerald-500 rounded-sm" />
              <span className="w-1.5 h-2 bg-emerald-500/50 rounded-sm" />
              <span className="w-1.5 h-1 bg-emerald-500/20 rounded-sm" />
            </div>
          </div>
          <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">
            {data?.tyre_compound || lapTiming?.compound || (activeMode === 'ENDURANCE' ? 'MEDIUM (C3)' : 'SOFT (C4)')}
          </span>
        </div>

        {/* Gauge 5: Front Left Brake Temp */}
        <F1Gauge
          title="Front Left Tyre Brake Temp"
          value={data?.brake_temp_fl || 830}
          min={0}
          max={1200}
          unit="°C"
          color="yellow"
          decimals={0}
        />

        {/* Gauge 6: Front Right Brake Temp */}
        <F1Gauge
          title="Front Right Tyre Brake Temp"
          value={data?.brake_temp_fr || 829}
          min={0}
          max={1200}
          unit="°C"
          color="yellow"
          decimals={0}
        />

        {/* Card 7: Fastest Lap */}
        <div className="bg-[#12151e] border border-[#232736] rounded-xl p-4 flex flex-col justify-between shadow-sm lg:col-span-1">
          <div className="flex justify-between items-center">
            <span className="text-[11px] font-mono text-slate-400">
              Fastest Lap
            </span>
            <span className="text-[9px] bg-purple-500/20 text-purple-400 font-bold px-1.5 py-0.5 rounded border border-purple-500/30">
              PURPLE
            </span>
          </div>
          <div className="my-auto text-purple-400 font-bold text-base leading-tight text-center lg:text-left font-mono">
            {lapTiming?.fastestLapFormatted || (activeMode === 'ENDURANCE' ? '1:24.230' : '1:20.161')}
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-400">
            <span className="truncate max-w-[130px]">{lapTiming?.fastestDriver || (activeMode === 'ENDURANCE' ? 'LECLERC (RACE)' : 'LECLERC (POLE)')}</span>
            <span className="text-purple-400 font-bold">LAP {lapTiming?.fastestLapNumber || 1}</span>
          </div>
        </div>

        {/* ROW 2 */}
        {/* Gauge 8: Current Speed */}
        <F1Gauge
          title="Current Speed"
          value={data?.speed || 0}
          min={0}
          max={360}
          unit="km/h"
          color="red"
          decimals={2}
        />

        {/* Gauge 9: Rear Left Tyre Wear */}
        <F1Gauge
          title="Rear Left Tyre Wear"
          value={data?.tyre_wear_rl || 11.0}
          min={0}
          max={100}
          unit="%"
          color="green"
          decimals={2}
        />

        {/* Gauge 10: Rear Right Tyre Wear */}
        <F1Gauge
          title="Rear Right Tyre Wear"
          value={data?.tyre_wear_rr || 10.0}
          min={0}
          max={100}
          unit="%"
          color="green"
          decimals={2}
        />

        {/* Gauge 11: Engine Damage / Condition */}
        <F1Gauge
          title="Engine Damage"
          value={data?.engine_damage || 10.0}
          min={0}
          max={100}
          unit="%"
          color="green"
          decimals={2}
        />

        {/* Gauge 12: Rear Left Brake Temp */}
        <F1Gauge
          title="Rear Left Tyre Brake Temp"
          value={data?.brake_temp_rl || 888}
          min={0}
          max={1200}
          unit="°C"
          color="yellow"
          decimals={0}
        />

        {/* Gauge 13: Rear Right Brake Temp */}
        <F1Gauge
          title="Rear Right Tyre Brake Temp"
          value={data?.brake_temp_rr || 887}
          min={0}
          max={1200}
          unit="°C"
          color="yellow"
          decimals={0}
        />

        {/* Card 14: Last Lap */}
        <div className="bg-[#12151e] border border-[#232736] rounded-xl p-4 flex flex-col justify-between shadow-sm lg:col-span-1">
          <span className="text-[11px] font-mono text-slate-400">
            Last Lap
          </span>
          <div className="my-auto text-emerald-400 font-bold text-sm leading-tight text-center lg:text-left font-mono">
            {lapTiming?.lastLapFormatted && lapTiming.lastLapFormatted !== '--:--.---'
              ? lapTiming.lastLapFormatted
              : (activeMode === 'ENDURANCE' ? '1:24.230' : '1:20.161')}
          </div>
          <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono">
            <span>DELTA: <strong className={lapTiming?.lastLapDelta === 'PURPLE' ? 'text-purple-400' : 'text-emerald-400'}>{lapTiming?.lastLapDelta || '±0.000'}</strong></span>
            <span className="text-amber-500 font-bold">{activeMode === 'ENDURANCE' ? 'STINT 1' : 'QUALI'}</span>
          </div>
        </div>

      </div>

      {/* ======================================================== */}
      {/* 3. TIME-SERIES CHARTS (MIDDLE ROW OF REFERENCE)          */}
      {/* ======================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* LEFT CHART: Car Engine RPM */}
        <div className="bg-[#12151e] border border-[#232736] rounded-xl p-4 flex flex-col h-72 shadow-sm">
          <div className="flex justify-between items-center mb-1 text-xs">
            <span className="font-bold text-slate-300">Car Engine RPM</span>
            <span className="text-[10px] text-cyan-400 flex items-center gap-1">
              <Clock size={11} /> Last 5 minutes
            </span>
          </div>
          
          {/* Subtitle Stats */}
          <div className="text-[11px] text-slate-400 mb-2 flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-emerald-500 inline-block" />
              car engine rpm
            </span>
            <span>Min: <strong className="text-white">{stats.rpmMin || 6000} rpm</strong></span>
            <span>Max: <strong className="text-white">{stats.rpmMax || 19500} rpm</strong></span>
            <span>Avg: <strong className="text-white">{stats.rpmAvg || 12000} rpm</strong></span>
          </div>

          <div className="flex-grow w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="rpmGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" hide />
                <YAxis domain={[5000, 20000]} stroke="#475569" fontSize={9} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px', borderRadius: '8px' }}
                  itemStyle={{ color: '#22c55e' }}
                  formatter={(val) => [`${val} rpm`, 'RPM']}
                />
                <Area type="monotone" dataKey="rpm" stroke="#22c55e" strokeWidth={1.5} fillOpacity={1} fill="url(#rpmGrad)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RIGHT CHART: Car Speed Monitor */}
        <div className="bg-[#12151e] border border-[#232736] rounded-xl p-4 flex flex-col h-72 shadow-sm">
          <div className="flex justify-between items-center mb-1 text-xs">
            <span className="font-bold text-slate-300">Car Speed Monitor</span>
            <span className="text-[10px] text-cyan-400 flex items-center gap-1">
              <Clock size={11} /> Last 5 minutes
            </span>
          </div>

          {/* Subtitle Stats */}
          <div className="text-[11px] text-slate-400 mb-2 flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-0.5 bg-emerald-500 inline-block" />
              car speed
            </span>
            <span>Min: <strong className="text-white">{stats.speedMin || 0} km/h</strong></span>
            <span>Max: <strong className="text-white">{stats.speedMax || 350} km/h</strong></span>
            <span>Avg: <strong className="text-white">{stats.speedAvg || 220} km/h</strong></span>
          </div>

          <div className="flex-grow w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="speedGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" hide />
                <YAxis domain={[0, 360]} stroke="#475569" fontSize={9} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px', borderRadius: '8px' }}
                  itemStyle={{ color: '#22c55e' }}
                  formatter={(val) => [`${val} km/h`, 'Speed']}
                />
                <Area type="monotone" dataKey="speed" stroke="#22c55e" strokeWidth={1.5} fillOpacity={1} fill="url(#speedGrad)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* ======================================================== */}
      {/* 4. DRIVING INPUTS & HARDWARE BUS TRACES (BOTTOM ROW)     */}
      {/* ======================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        
        {/* LEFT CHART: Throttle (%) & Brake (%) Overlay */}
        <div className="bg-[#12151e] border border-[#232736] rounded-xl p-4 flex flex-col h-64 shadow-sm">
          <div className="flex justify-between items-center mb-1 text-xs">
            <span className="font-bold text-slate-300">Driver Pedal Inputs (Throttle vs Brake)</span>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="text-cyan-400">THR: <strong className="text-white">{data?.throttle?.toFixed(0) || 0}%</strong></span>
              <span className="text-red-400">BRK: <strong className="text-white">{data?.brake_pressure?.toFixed(0) || 0}%</strong></span>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 mb-2 flex items-center gap-6">
            <span className="flex items-center gap-1.5 text-cyan-400">
              <span className="w-2.5 h-0.5 bg-cyan-400 inline-block" /> Throttle (%)
            </span>
            <span className="flex items-center gap-1.5 text-red-400">
              <span className="w-2.5 h-0.5 bg-red-500 inline-block" /> Brake (%)
            </span>
            <span className="text-slate-500">Gear: <strong className="text-white bg-[#1b2030] px-1.5 py-0.2 rounded border border-[#2a324b]">G{data?.gear || 1}</strong></span>
          </div>

          <div className="flex-grow w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="time" hide />
                <YAxis domain={[0, 100]} stroke="#475569" fontSize={9} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px', borderRadius: '8px' }}
                />
                <Line type="monotone" dataKey="throttle" stroke="#06b6d4" strokeWidth={2} dot={false} isAnimationActive={false} name="Throttle (%)" />
                <Line type="monotone" dataKey="brake" stroke="#ef4444" strokeWidth={2} dot={false} isAnimationActive={false} name="Brake (%)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* RIGHT CHART: ESP32 Electrical & System Power */}
        <div className="bg-[#12151e] border border-[#232736] rounded-xl p-4 flex flex-col h-64 shadow-sm">
          <div className="flex justify-between items-center mb-1 text-xs">
            <span className="font-bold text-slate-300 flex items-center gap-2">
              <Cpu size={14} className="text-amber-400" />
              ESP32 Telemetry Transceiver & Electrical Bus
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              Link: WiFi 50Hz
            </span>
          </div>

          <div className="grid grid-cols-4 gap-2 my-2 text-center text-xs">
            <div className="bg-[#181c29] p-2 rounded border border-[#262c3e]">
              <span className="text-[10px] text-slate-400 block">BUS VOLTAGE</span>
              <span className="font-bold text-amber-400">{data?.battery_voltage?.toFixed(2) || "14.20"} V</span>
            </div>
            <div className="bg-[#181c29] p-2 rounded border border-[#262c3e]">
              <span className="text-[10px] text-slate-400 block">CURRENT</span>
              <span className="font-bold text-amber-400">{data?.battery_current?.toFixed(2) || "2.50"} A</span>
            </div>
            <div className="bg-[#181c29] p-2 rounded border border-[#262c3e]">
              <span className="text-[10px] text-slate-400 block">POWER</span>
              <span className="font-bold text-emerald-400">{data?.powerKW?.toFixed(2) || "0.04"} kW</span>
            </div>
            <div className="bg-[#181c29] p-2 rounded border border-[#262c3e]">
              <span className="text-[10px] text-slate-400 block">COOLANT TEMP</span>
              <span className="font-bold text-cyan-400">{data?.coolant_temp?.toFixed(1) || "92.5"} °C</span>
            </div>
          </div>

          <div className="flex-grow w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="powerGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <XAxis dataKey="time" hide />
                <YAxis domain={[0, 0.1]} stroke="#475569" fontSize={9} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '11px', borderRadius: '8px' }}
                  itemStyle={{ color: '#f59e0b' }}
                  formatter={(val) => [`${val} kW`, 'Electrical Power']}
                />
                <Area type="monotone" dataKey="powerKW" stroke="#f59e0b" strokeWidth={1.5} fillOpacity={1} fill="url(#powerGrad)" isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

    </div>
  );
}
