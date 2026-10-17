// src/pages/Powertrain.jsx
import React from 'react';
import { Activity, Gauge, Zap, Crosshair, Compass, Cpu } from 'lucide-react';

export default function Powertrain({ data }) {
  // G-Force Friction Circle: ax = longitudinal (+accel / -brake), ay = lateral (+right / -left)
  // Max scale: 3.5 G
  const maxG = 3.5;
  const gX = data?.ay || 0; // Lateral
  const gY = data?.ax || 0; // Longitudinal

  const plotX = Math.min(Math.max((gX / maxG) * 50 + 50, 2), 98);
  const plotY = Math.min(Math.max((-gY / maxG) * 50 + 50, 2), 98);

  return (
    <div className="flex flex-col gap-5 w-full max-w-[1920px] mx-auto font-mono text-slate-200">
      
      {/* ======================================================== */}
      {/* 1. TOP KPI ROW                                           */}
      {/* ======================================================== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 shrink-0">
        <div className="bg-[#12151e] p-5 rounded-xl border border-[#232736] flex flex-col justify-between shadow-sm hover:border-[#353b52] transition-colors">
          <span className="text-[11px] text-slate-400 flex items-center gap-2">
            <Activity size={15} className="text-cyan-400" /> RESULTANT G-FORCE
          </span>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-4xl font-black text-cyan-400">{data?.resultantG?.toFixed(2) || "0.00"}</span>
            <span className="text-lg text-slate-500 font-bold">G</span>
          </div>
          <span className="text-[10px] text-slate-500 uppercase">3-Axis Vector Sum</span>
        </div>

        <div className="bg-[#12151e] p-5 rounded-xl border border-[#232736] flex flex-col justify-between shadow-sm hover:border-[#353b52] transition-colors">
          <span className="text-[11px] text-slate-400 flex items-center gap-2">
            <Gauge size={15} className="text-amber-400" /> WHEEL SLIP DELTA
          </span>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-4xl font-black text-amber-400">{data?.wheelSlipDelta?.toFixed(1) || "0.0"}</span>
            <span className="text-lg text-slate-500 font-bold">km/h</span>
          </div>
          <span className="text-[10px] text-slate-500 uppercase">Driven vs Rolling Axle</span>
        </div>

        <div className="bg-[#12151e] p-5 rounded-xl border border-[#232736] flex flex-col justify-between shadow-sm hover:border-[#353b52] transition-colors">
          <span className="text-[11px] text-slate-400 flex items-center gap-2">
            <Zap size={15} className="text-emerald-400" /> ELECTRICAL POWER
          </span>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-4xl font-black text-emerald-400">{data?.powerKW?.toFixed(2) || "0.00"}</span>
            <span className="text-lg text-slate-500 font-bold">kW</span>
          </div>
          <span className="text-[10px] text-slate-500 uppercase">{data?.battery_voltage?.toFixed(1) || 14.2}V @ {data?.battery_current?.toFixed(1) || 2.5}A</span>
        </div>

        <div className="bg-[#12151e] p-5 rounded-xl border border-[#232736] flex flex-col justify-between shadow-sm hover:border-[#353b52] transition-colors">
          <span className="text-[11px] text-slate-400 flex items-center gap-2">
            <Crosshair size={15} className="text-purple-400" /> CORNERING INTENSITY
          </span>
          <div className="my-2 flex items-baseline gap-2">
            <span className="text-4xl font-black text-purple-400">{data?.corneringIntensity || 0}</span>
            <span className="text-lg text-slate-500 font-bold">%</span>
          </div>
          <span className="text-[10px] text-slate-500 uppercase">Lateral Chassis Load</span>
        </div>
      </div>
      
      {/* ======================================================== */}
      {/* 2. MAIN TELEMETRY MATRICES                                */}
      {/* ======================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-grow">
        
        {/* COLUMN 1: 6-Axis IMU Sensor Array */}
        <div className="lg:col-span-4 bg-[#12151e] p-5 rounded-xl border border-[#232736] flex flex-col shadow-sm">
          <div className="flex justify-between items-center mb-4 border-b border-[#232736] pb-3">
            <span className="text-xs text-slate-300 font-bold flex items-center gap-2">
              <Compass size={15} className="text-cyan-400" /> 6-AXIS IMU VELOCITIES
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              CALIBRATED
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 flex-grow">
            <div className="p-3.5 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col justify-between">
              <span className="text-slate-400 text-[10px]">ACCEL X (Longitudinal)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-white">{data?.ax?.toFixed(2) || "0.00"}</span>
                <span className="text-[10px] text-slate-500">m/s²</span>
              </div>
            </div>

            <div className="p-3.5 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col justify-between">
              <span className="text-slate-400 text-[10px]">GYRO X (Roll Rate)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-cyan-400">{data?.gx?.toFixed(1) || "0.0"}</span>
                <span className="text-[10px] text-slate-500">°/s</span>
              </div>
            </div>

            <div className="p-3.5 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col justify-between">
              <span className="text-slate-400 text-[10px]">ACCEL Y (Lateral)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-white">{data?.ay?.toFixed(2) || "0.00"}</span>
                <span className="text-[10px] text-slate-500">m/s²</span>
              </div>
            </div>

            <div className="p-3.5 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col justify-between">
              <span className="text-slate-400 text-[10px]">GYRO Y (Pitch Rate)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-cyan-400">{data?.gy?.toFixed(1) || "0.0"}</span>
                <span className="text-[10px] text-slate-500">°/s</span>
              </div>
            </div>

            <div className="p-3.5 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col justify-between">
              <span className="text-slate-400 text-[10px]">ACCEL Z (Vertical)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-white">{data?.az?.toFixed(2) || "9.81"}</span>
                <span className="text-[10px] text-slate-500">m/s²</span>
              </div>
            </div>

            <div className="p-3.5 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col justify-between">
              <span className="text-slate-400 text-[10px]">GYRO Z (Yaw Rate)</span>
              <div className="flex items-baseline justify-between mt-1">
                <span className="text-2xl font-bold text-purple-400">{data?.gz?.toFixed(1) || "0.0"}</span>
                <span className="text-[10px] text-slate-500">°/s</span>
              </div>
            </div>
          </div>
        </div>

        {/* COLUMN 2: G-Force Friction Circle (Traction Envelope) */}
        <div className="lg:col-span-4 bg-[#12151e] p-5 rounded-xl border border-[#232736] flex flex-col items-center justify-between shadow-sm relative overflow-hidden">
          <div className="w-full flex justify-between items-center mb-2 border-b border-[#232736] pb-3">
            <span className="text-xs text-slate-300 font-bold">
              G-FORCE TRACTION CIRCLE
            </span>
            <span className="text-[10px] text-cyan-400">
              SCALE: ±3.5G
            </span>
          </div>
          
          <div className="relative w-full max-w-[280px] aspect-square bg-[#10131b] rounded-full border-2 border-[#232736] my-4 shadow-inner flex items-center justify-center">
            {/* Crosshairs */}
            <div className="absolute top-0 bottom-0 left-1/2 w-[1px] bg-[#2e354a] -translate-x-1/2" />
            <div className="absolute left-0 right-0 top-1/2 h-[1px] bg-[#2e354a] -translate-y-1/2" />
            
            {/* Concentric G-Rings */}
            <div className="absolute w-[85%] h-[85%] rounded-full border border-dashed border-[#2e354a]/60" />
            <div className="absolute w-[56%] h-[56%] rounded-full border border-dashed border-[#2e354a]/80" />
            <div className="absolute w-[28%] h-[28%] rounded-full border border-[#2e354a]" />

            {/* Scale ring labels */}
            <span className="absolute top-[8%] left-1/2 -translate-x-1/2 text-[8px] text-slate-500">3.0G</span>
            <span className="absolute top-[22%] left-1/2 -translate-x-1/2 text-[8px] text-slate-500">2.0G</span>
            <span className="absolute top-[36%] left-1/2 -translate-x-1/2 text-[8px] text-slate-500">1.0G</span>

            {/* Axis Cardinal Labels */}
            <span className="absolute top-2 left-1/2 -translate-x-1/2 text-[9px] text-emerald-400 font-bold">ACCEL</span>
            <span className="absolute bottom-2 left-1/2 -translate-x-1/2 text-[9px] text-red-400 font-bold">BRAKE</span>
            <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[9px] text-cyan-400 font-bold">LEFT</span>
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] text-cyan-400 font-bold">RIGHT</span>
            
            {/* Moving G-Force Traction Dot */}
            <div 
              className="absolute w-4 h-4 bg-cyan-400 rounded-full shadow-[0_0_15px_#22d3ee] transition-all duration-200 ease-out transform -translate-x-1/2 -translate-y-1/2 border-2 border-white"
              style={{ left: `${plotX}%`, top: `${plotY}%` }}
            />
          </div>

          <div className="w-full flex justify-between items-center text-[10px] text-slate-400 pt-2 border-t border-[#232736]">
            <span>LAT: <strong className="text-white">{data?.ay?.toFixed(2) || "0.00"} G</strong></span>
            <span>LONG: <strong className="text-white">{data?.ax?.toFixed(2) || "0.00"} G</strong></span>
            <span>TOTAL: <strong className="text-cyan-400">{data?.resultantG?.toFixed(2) || "0.00"} G</strong></span>
          </div>
        </div>

        {/* COLUMN 3: Individual Wheel Speed Chassis Matrix */}
        <div className="lg:col-span-4 bg-[#12151e] p-5 rounded-xl border border-[#232736] flex flex-col shadow-sm">
          <div className="flex justify-between items-center mb-4 border-b border-[#232736] pb-3">
            <span className="text-xs text-slate-300 font-bold">
              4-CORNER WHEEL SPEED MATRIX
            </span>
            <span className="text-[10px] text-amber-400">
              RWD BIAS
            </span>
          </div>

          <div className="grid grid-cols-2 gap-3 flex-grow">
            {/* FRONT LEFT */}
            <div className="p-4 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col items-center justify-center gap-1">
              <span className="text-slate-400 text-[10px]">FRONT LEFT (FL)</span>
              <span className="text-2xl font-bold text-cyan-400">{data?.wheel_fl?.toFixed(1) || "0.0"}</span>
              <span className="text-slate-500 text-[9px]">KM/H</span>
            </div>

            {/* FRONT RIGHT */}
            <div className="p-4 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col items-center justify-center gap-1">
              <span className="text-slate-400 text-[10px]">FRONT RIGHT (FR)</span>
              <span className="text-2xl font-bold text-cyan-400">{data?.wheel_fr?.toFixed(1) || "0.0"}</span>
              <span className="text-slate-500 text-[9px]">KM/H</span>
            </div>

            {/* REAR LEFT */}
            <div className="p-4 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col items-center justify-center gap-1">
              <span className="text-slate-400 text-[10px]">REAR LEFT (RL)</span>
              <span className="text-2xl font-bold text-emerald-400">{data?.wheel_rl?.toFixed(1) || "0.0"}</span>
              <span className="text-slate-500 text-[9px]">KM/H (DRIVEN)</span>
            </div>

            {/* REAR RIGHT */}
            <div className="p-4 bg-[#181c29] rounded-lg border border-[#262c3e] flex flex-col items-center justify-center gap-1">
              <span className="text-slate-400 text-[10px]">REAR RIGHT (RR)</span>
              <span className="text-2xl font-bold text-emerald-400">{data?.wheel_rr?.toFixed(1) || "0.0"}</span>
              <span className="text-slate-500 text-[9px]">KM/H (DRIVEN)</span>
            </div>
          </div>

          <div className="mt-3 p-2 bg-[#181c29] rounded border border-[#262c3e] text-center text-[10px] text-slate-400">
            DRIVE AXLE SLIP: <strong className="text-amber-400">{data?.wheelSlipDelta?.toFixed(1) || "0.0"} km/h</strong>
          </div>
        </div>

      </div>
    </div>
  );
}