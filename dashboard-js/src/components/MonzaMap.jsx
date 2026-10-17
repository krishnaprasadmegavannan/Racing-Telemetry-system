// src/components/MonzaMap.jsx
import React from 'react';
import trackData from '../assets/monza_fastf1_track.json';

export default function MonzaMap({ 
  track_x, 
  track_y, 
  speed = 0, 
  brake = 0, 
  throttle = 0, 
  gear = 1,
  cornerName = '',
  sector = 1,
  lat = 45.618,
  lon = 9.281
}) {
  const meta = trackData.metadata || {};
  const pathD = meta.svg_path || '';
  const landmarks = meta.landmarks || [];

  // Fallback to start/finish if coordinates are 0
  const carX = (track_x && track_x > 10) ? track_x : 741.6;
  const carY = (track_y && track_y > 10) ? track_y : 473.2;

  const isBraking = brake > 15;
  const isFullThrottle = throttle > 85;
  const dotColor = isBraking ? '#ef4444' : isFullThrottle ? '#10b981' : '#38bdf8';

  return (
    <div className="w-full bg-[#12151e] rounded-xl border border-[#232736] flex flex-col justify-between p-3.5 shadow-sm overflow-hidden select-none">
      
      {/* TOP CIRCUIT INFO OVERLAY */}
      <div className="w-full flex flex-wrap justify-between items-center z-20 text-xs px-2.5 py-1.5 bg-[#181c29] rounded-lg border border-[#262c3e] gap-2">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-white font-bold tracking-wider text-[11px]">
            AUTODROMO NAZIONALE MONZA
          </span>
          <span className="text-slate-400 text-[10px] hidden sm:inline">
            5,793 km // FastF1 GPS Trace
          </span>
        </div>

        <div className="flex items-center gap-3 text-[10px]">
          <span className="text-slate-400">
            LAT: <strong className="text-white">{lat ? lat.toFixed(4) : "45.6180"}</strong> | LON: <strong className="text-white">{lon ? lon.toFixed(4) : "9.2810"}</strong>
          </span>
          <span className="text-slate-400">
            SEC: <strong className={`font-bold ${sector === 1 ? 'text-cyan-400' : sector === 2 ? 'text-purple-400' : 'text-emerald-400'}`}>S{sector}</strong>
          </span>
          <span className="bg-[#1b2133] px-2 py-0.5 rounded border border-[#2c354e] text-slate-200">
            ZONE: <strong className="text-amber-400 font-bold">{cornerName || "Main Straight"}</strong>
          </span>
        </div>
      </div>

      {/* SVG CIRCUIT CONTAINER - Bounded aspect ratio, never extends or overflows */}
      <div className="relative w-full aspect-[1000/520] max-h-[380px] flex items-center justify-center my-2 mx-auto">
        <svg
          viewBox="0 0 1000 520"
          className="w-full h-full object-contain"
        >
          <defs>
            {/* Track glow filter */}
            <filter id="trackGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
            
            {/* Car marker glow */}
            <filter id="carGlow" x="-50%" y="-50%" width="200%" height="200%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>

            {/* Gradient along track */}
            <linearGradient id="sectorGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" />
              <stop offset="50%" stopColor="#a855f7" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
          </defs>

          {/* 1. Track Runoff / Ambient Foundation */}
          <path
            d={pathD}
            fill="none"
            stroke="#161c2c"
            strokeWidth="32"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* 2. Track Asphalt Core */}
          <path
            d={pathD}
            fill="none"
            stroke="#0d111a"
            strokeWidth="20"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* 3. Outer Track Border Curbs */}
          <path
            d={pathD}
            fill="none"
            stroke="#263147"
            strokeWidth="16"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="8 6"
          />

          {/* 4. Active Circuit Neon Centerline */}
          <path
            d={pathD}
            fill="none"
            stroke="url(#sectorGrad)"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="0.85"
            filter="url(#trackGlow)"
          />

          {/* 5. Start / Finish Line Checkered Marker */}
          <g transform="translate(741.6, 473.2)">
            <line x1="0" y1="-14" x2="0" y2="14" stroke="#ffffff" strokeWidth="4" strokeDasharray="3 3" />
            <text x="8" y="24" fill="#94a3b8" fontSize="9" fontFamily="monospace" fontWeight="bold">S/F LINE</text>
          </g>

          {/* 6. Corner & Sector Landmarks */}
          {landmarks.map((lm, idx) => (
            <g key={idx} transform={`translate(${lm.x}, ${lm.y})`} className="opacity-75 hover:opacity-100 transition-opacity">
              <circle r="3" fill="#64748b" stroke="#0f172a" strokeWidth="1.5" />
              <text
                x="6"
                y="-6"
                fill="#94a3b8"
                fontSize="9"
                fontFamily="monospace"
                fontWeight="bold"
                className="pointer-events-none select-none drop-shadow"
              >
                {lm.name}
              </text>
            </g>
          ))}

          {/* 7. Live Car Position Beacon */}
          <g transform={`translate(${carX}, ${carY})`} className="transition-all duration-200 ease-linear">
            {/* Outer Pulsing Halo */}
            <circle
              r="14"
              fill={dotColor}
              opacity="0.25"
              className="animate-ping"
            />
            
            {/* Medium Halo */}
            <circle
              r="8"
              fill={dotColor}
              opacity="0.5"
              filter="url(#carGlow)"
            />

            {/* Solid Center Dot */}
            <circle
              r="4.5"
              fill="#ffffff"
              stroke={dotColor}
              strokeWidth="2"
            />

            {/* Floating Car Telemetry Tag */}
            <g transform="translate(10, -14)">
              <rect
                x="-2"
                y="-11"
                width="84"
                height="18"
                rx="4"
                fill="#0f1422"
                stroke={dotColor}
                strokeWidth="1"
                opacity="0.95"
              />
              <text
                x="40"
                y="1"
                fill="#ffffff"
                fontSize="9"
                fontFamily="monospace"
                fontWeight="black"
                textAnchor="middle"
              >
                {Math.round(speed)} km/h G{gear}
              </text>
            </g>
          </g>
        </svg>
      </div>

      {/* BOTTOM TELEMETRY TELEGRAPH */}
      <div className="w-full grid grid-cols-4 gap-2 text-center text-xs pt-2 border-t border-[#1f2638] z-20">
        <div className="bg-[#181c29] py-1.5 px-2 rounded-lg border border-[#232a3e]">
          <span className="text-[9px] text-slate-400 block">SPEED</span>
          <span className="text-white font-bold text-sm">{Math.round(speed)} <span className="text-[10px] text-slate-500 font-normal">km/h</span></span>
        </div>
        <div className="bg-[#181c29] py-1.5 px-2 rounded-lg border border-[#232a3e]">
          <span className="text-[9px] text-slate-400 block">THROTTLE</span>
          <span className="text-cyan-400 font-bold text-sm">{Math.round(throttle)}%</span>
        </div>
        <div className="bg-[#181c29] py-1.5 px-2 rounded-lg border border-[#232a3e]">
          <span className="text-[9px] text-slate-400 block">BRAKE</span>
          <span className={`font-bold text-sm ${isBraking ? 'text-red-400' : 'text-slate-400'}`}>{Math.round(brake)}%</span>
        </div>
        <div className="bg-[#181c29] py-1.5 px-2 rounded-lg border border-[#232a3e]">
          <span className="text-[9px] text-slate-400 block">GEAR</span>
          <span className="text-emerald-400 font-bold text-sm">G{gear}</span>
        </div>
      </div>

    </div>
  );
}