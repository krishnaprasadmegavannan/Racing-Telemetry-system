// src/pages/Diagnostics.jsx
import React from 'react';
import { Terminal, Cpu, Satellite, Compass, Activity, Thermometer } from 'lucide-react';

export default function Diagnostics({ data }) {
  const DataRow = ({ label, value, unit = "" }) => (
    <div className="flex justify-between items-center py-1.5 border-b border-[#232736]/60 last:border-0 hover:bg-[#1e2334]/50 transition-colors px-2 rounded">
      <span className="text-slate-400 text-[11px]">{label}</span>
      <span className="font-bold text-white tracking-wider text-[11px]">
        {value !== undefined && value !== null ? value : "---"} {unit && <span className="text-slate-500 font-normal">{unit}</span>}
      </span>
    </div>
  );

  return (
    <div className="bg-[#12151e] p-5 rounded-xl border border-[#232736] font-mono text-xs w-full max-w-[1920px] mx-auto h-full flex flex-col shadow-sm text-slate-200">
      
      {/* HEADER STATUS STRIP */}
      <div className="flex flex-wrap justify-between items-center mb-5 border-b border-[#232736] pb-3.5 shrink-0 gap-3">
        <span className="text-xs font-bold text-cyan-400 flex items-center gap-2 uppercase tracking-widest">
          <Cpu size={16} className="text-cyan-400" />
          Complete Telemetry Schema & Hardware Bus Inspector
        </span>
        <div className="text-[10px] text-slate-400 flex flex-wrap gap-2.5 bg-[#181c29] px-3.5 py-1.5 rounded-lg border border-[#262c3e]">
          <span>SEQ: <strong className="text-white font-bold">{data?.sequence_number || 0}</strong></span>
          <span>•</span>
          <span>TIME: <strong className="text-white font-bold">{data?.timestamp ? new Date(data.timestamp * 1000).toISOString().substr(11, 8) : "00:00:00"}</strong></span>
          <span>•</span>
          <span>RATE: <strong className="text-white font-bold">50 Hz</strong></span>
          <span>•</span>
          <span>LINK: <strong className="text-emerald-400 font-bold">{data?.transmission_information || "WiFi"}</strong></span>
          <span>•</span>
          <span>STATUS: <strong className="text-emerald-400 font-bold">{data?.status_error_information || "OK"}</strong></span>
        </div>
      </div>

      {/* TOP METRICS 4-CARD GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 shrink-0">
        
        {/* CARD 1: GPS MODULE */}
        <div className="p-4 bg-[#181c29] rounded-xl border border-[#262c3e] flex flex-col justify-between">
          <span className="text-amber-400 font-bold flex items-center gap-2 mb-3 border-b border-[#262c3e] pb-2 text-[11px]">
            <Satellite size={14} /> GPS TELEMETRY (6)
          </span>
          <div className="space-y-0.5">
            <DataRow label="latitude" value={data?.latitude?.toFixed(6)} />
            <DataRow label="longitude" value={data?.longitude?.toFixed(6)} />
            <DataRow label="speed" value={data?.speed?.toFixed(1)} unit="km/h" />
            <DataRow label="altitude" value={data?.altitude?.toFixed(1)} unit="m" />
            <DataRow label="satellites" value={data?.satellite_count} />
            <DataRow label="fix_status" value={data?.fix_status} />
          </div>
        </div>

        {/* CARD 2: IMU ACCELERATION */}
        <div className="p-4 bg-[#181c29] rounded-xl border border-[#262c3e] flex flex-col justify-between">
          <span className="text-cyan-400 font-bold flex items-center gap-2 mb-3 border-b border-[#262c3e] pb-2 text-[11px]">
            <Compass size={14} /> 6-AXIS IMU (6)
          </span>
          <div className="space-y-0.5">
            <DataRow label="ax (Longitudinal)" value={data?.ax?.toFixed(2)} unit="m/s²" />
            <DataRow label="ay (Lateral)" value={data?.ay?.toFixed(2)} unit="m/s²" />
            <DataRow label="az (Vertical)" value={data?.az?.toFixed(2)} unit="m/s²" />
            <DataRow label="gx (Roll Rate)" value={data?.gx?.toFixed(1)} unit="°/s" />
            <DataRow label="gy (Pitch Rate)" value={data?.gy?.toFixed(1)} unit="°/s" />
            <DataRow label="gz (Yaw Rate)" value={data?.gz?.toFixed(1)} unit="°/s" />
          </div>
        </div>

        {/* CARD 3: POWERTRAIN & ELECTRICAL */}
        <div className="p-4 bg-[#181c29] rounded-xl border border-[#262c3e] flex flex-col justify-between">
          <span className="text-emerald-400 font-bold flex items-center gap-2 mb-3 border-b border-[#262c3e] pb-2 text-[11px]">
            <Activity size={14} /> POWERTRAIN & CAN (6)
          </span>
          <div className="space-y-0.5">
            <DataRow label="gear" value={data?.gear ? `G${data.gear}` : "G1"} />
            <DataRow label="rpm" value={data?.rpm?.toFixed(0)} unit="rpm" />
            <DataRow label="throttle" value={data?.throttle?.toFixed(0)} unit="%" />
            <DataRow label="brake_pressure" value={data?.brake_pressure?.toFixed(0)} unit="%" />
            <DataRow label="battery_voltage" value={data?.battery_voltage?.toFixed(2)} unit="V" />
            <DataRow label="battery_current" value={data?.battery_current?.toFixed(2)} unit="A" />
          </div>
        </div>

        {/* CARD 4: THERMALS & BRAKES */}
        <div className="p-4 bg-[#181c29] rounded-xl border border-[#262c3e] flex flex-col justify-between">
          <span className="text-purple-400 font-bold flex items-center gap-2 mb-3 border-b border-[#262c3e] pb-2 text-[11px]">
            <Thermometer size={14} /> THERMAL CHANNELS (6)
          </span>
          <div className="space-y-0.5">
            <DataRow label="coolant_temp" value={data?.coolant_temp?.toFixed(1)} unit="°C" />
            <DataRow label="engine_temp" value={data?.engine_temp?.toFixed(1)} unit="°C" />
            <DataRow label="brake_temp_fl" value={data?.brake_temp_fl?.toFixed(0)} unit="°C" />
            <DataRow label="brake_temp_fr" value={data?.brake_temp_fr?.toFixed(0)} unit="°C" />
            <DataRow label="brake_temp_rl" value={data?.brake_temp_rl?.toFixed(0)} unit="°C" />
            <DataRow label="brake_temp_rr" value={data?.brake_temp_rr?.toFixed(0)} unit="°C" />
          </div>
        </div>

      </div>

      {/* BOTTOM TERMINAL: LIVE JSON STREAM */}
      <div className="mt-5 flex-grow flex flex-col bg-[#10131b] rounded-xl border border-[#232736] overflow-hidden shadow-inner">
        <div className="bg-[#181c29] px-4 py-2.5 border-b border-[#232736] text-slate-300 font-bold flex justify-between items-center shrink-0 text-xs">
          <span className="flex items-center gap-2">
            <Terminal size={14} className="text-emerald-400" />
            LIVE SERIAL / WEBSOCKET PAYLOAD (RAW ESP32 PACKET)
          </span>
          <span className="text-emerald-400 text-[10px] bg-emerald-500/10 px-2.5 py-0.5 rounded border border-emerald-500/20">
            CONNECTED 50Hz
          </span>
        </div>
        <div className="p-4 overflow-y-auto max-h-60 flex-grow text-[11px] text-cyan-400/90 leading-relaxed scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      </div>

    </div>
  );
}