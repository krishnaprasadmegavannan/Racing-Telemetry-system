// src/components/SuperbikeCluster.jsx
import React from 'react';

export default function SuperbikeCluster({ rpm = 0, speed = 0, throttle = 0, brake = 0, gear = 1 }) {
  const maxRPM = 15000;
  const clampedRPM = Math.min(Math.max(rpm, 0), maxRPM);
  const rpmPct = clampedRPM / maxRPM;
  
  const numLEDs = 15;
  const activeLEDs = Math.floor(rpmPct * numLEDs);
  const isRedline = clampedRPM >= 12000;

  const radius = 85;
  const strokeWidth = 9;
  const cx = 130;
  const cy = 115;
  const startAngle = 150;
  const totalSweep = 240;
  const currentAngle = startAngle + (rpmPct * totalSweep);

  const polarToCartesian = (x, y, r, angleInDegrees) => {
    const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
    return {
      x: x + r * Math.cos(angleInRadians),
      y: y + r * Math.sin(angleInRadians)
    };
  };

  const describeArc = (x, y, r, sAngle, eAngle) => {
    const start = polarToCartesian(x, y, r, eAngle);
    const end = polarToCartesian(x, y, r, sAngle);
    const largeArcFlag = eAngle - sAngle <= 180 ? "0" : "1";
    return ["M", start.x, start.y, "A", r, r, 0, largeArcFlag, 0, end.x, end.y].join(" ");
  };

  return (
    <div className="bg-[#12151e] border border-[#232736] rounded-xl p-3.5 flex flex-col items-center justify-between shadow-sm relative overflow-hidden select-none">
      
      {/* COMPACT SHIFT LIGHT ARRAY */}
      <div className="flex gap-1 mb-2 px-2.5 py-1 bg-[#181c29] rounded-lg border border-[#262c3e]">
        {Array.from({ length: numLEDs }).map((_, i) => {
          let ledColor = "bg-emerald-500 shadow-[0_0_6px_#10b981]";
          if (i >= 7 && i < 11) ledColor = "bg-amber-400 shadow-[0_0_6px_#f59e0b]";
          if (i >= 11) ledColor = "bg-red-500 shadow-[0_0_6px_#ef4444]";

          const isActive = i < activeLEDs;
          return (
            <div 
              key={i} 
              className={`w-3 h-1.5 rounded-xs transition-all duration-75 ${
                isActive ? ledColor : 'bg-[#232838]'
              }`}
            />
          );
        })}
      </div>

      {/* COMPACT TACHOMETER & SPEEDOMETER GAUGE */}
      <div className="relative w-48 h-38 flex items-center justify-center my-0.5">
        <svg className="w-full h-full overflow-visible" viewBox="0 0 260 210">
          {/* Background Track */}
          <path
            d={describeArc(cx, cy, radius, startAngle, startAngle + totalSweep)}
            fill="none"
            stroke="#1b2130"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />
          {/* Dynamic RPM Arc */}
          {clampedRPM > 0 && (
            <path
              d={describeArc(cx, cy, radius, startAngle, currentAngle)}
              fill="none"
              stroke={isRedline ? "#ef4444" : clampedRPM > 10500 ? "#f59e0b" : "#22c55e"}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              className="transition-all duration-100"
              style={{
                filter: isRedline 
                  ? 'drop-shadow(0 0 6px rgba(239, 68, 68, 0.7))'
                  : 'drop-shadow(0 0 5px rgba(34, 197, 94, 0.4))'
              }}
            />
          )}

          {/* Scale Labels */}
          {[0, 3, 6, 9, 12, 15].map((kRPM) => {
            const angle = startAngle + ((kRPM / 15) * totalSweep);
            const pt = polarToCartesian(cx, cy, radius - 18, angle);
            return (
              <text
                key={kRPM}
                x={pt.x}
                y={pt.y}
                fill="#64748b"
                fontSize="9"
                fontFamily="monospace"
                fontWeight="bold"
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {kRPM}k
              </text>
            );
          })}
        </svg>

        {/* CENTER DIGITAL SPEED & GEAR */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center mt-2">
          <div className="flex items-baseline gap-1">
            <span className="text-3xl font-black tracking-tight text-white font-mono leading-none">
              {Math.round(speed)}
            </span>
            <span className="text-[10px] font-mono font-bold text-slate-400">KM/H</span>
          </div>

          <div className="mt-1 flex items-center gap-1.5 font-mono">
            <span className="text-[10px] text-slate-500 font-bold">GEAR</span>
            <span className="text-base font-black text-emerald-400 bg-[#181c29] px-2 py-0.2 rounded border border-[#262c3e] leading-tight">
              G{gear}
            </span>
          </div>

          <div className="text-[10px] font-mono text-slate-400 mt-1">
            <span className="text-white font-bold">{Math.round(clampedRPM)}</span> <span className="text-slate-500">RPM</span>
          </div>
        </div>
      </div>

      {/* THROTTLE & BRAKE TELEMETRY MINI BARS */}
      <div className="w-full grid grid-cols-2 gap-2 mt-2 font-mono text-xs">
        <div className="bg-[#181c29] p-2 rounded-lg border border-[#262c3e]">
          <div className="flex justify-between text-slate-400 mb-1 text-[10px]">
            <span>THROTTLE</span>
            <span className="text-cyan-400 font-bold">{Math.round(throttle)}%</span>
          </div>
          <div className="w-full bg-[#10131b] h-1.5 rounded overflow-hidden border border-[#232736]">
            <div className="bg-cyan-500 h-full transition-all duration-100" style={{ width: `${Math.min(100, Math.max(0, throttle))}%` }} />
          </div>
        </div>

        <div className="bg-[#181c29] p-2 rounded-lg border border-[#262c3e]">
          <div className="flex justify-between text-slate-400 mb-1 text-[10px]">
            <span>BRAKE</span>
            <span className="text-red-400 font-bold">{Math.round(brake)}%</span>
          </div>
          <div className="w-full bg-[#10131b] h-1.5 rounded overflow-hidden border border-[#232736]">
            <div className="bg-red-500 h-full transition-all duration-100" style={{ width: `${Math.min(100, Math.max(0, brake))}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
}