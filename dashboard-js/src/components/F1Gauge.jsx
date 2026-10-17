// src/components/F1Gauge.jsx
import React from 'react';

export default function F1Gauge({
  title,
  value = 0,
  min = 0,
  max = 100,
  unit = '',
  color = 'green', // 'green' | 'yellow' | 'red' | 'cyan' | 'multi'
  decimals = 2,
}) {
  const clampedValue = Math.min(Math.max(value, min), max);
  const percentage = (clampedValue - min) / (max - min || 1);

  // Semicircular arc from 180 deg (left) to 0 deg (right)
  const radius = 62;
  const strokeWidth = 10;
  const cx = 85;
  const cy = 78;

  // Arc calculations
  const startAngle = Math.PI; // 180 degrees (left)
  const endAngle = 0;         // 0 degrees (right)
  const sweepAngle = Math.PI; // 180 degree span
  const currentAngle = startAngle - (percentage * sweepAngle);

  // SVG coordinates
  const startX = cx - radius;
  const startY = cy;
  const endX = cx + radius;
  const endY = cy;

  const curX = cx + radius * Math.cos(currentAngle);
  const curY = cy - radius * Math.sin(currentAngle);

  // Color schemes matching the reference image
  const colorMap = {
    green: {
      stroke: '#22c55e',
      text: 'text-emerald-400',
      bgGlow: 'rgba(34, 197, 94, 0.2)',
    },
    yellow: {
      stroke: '#eab308',
      text: 'text-amber-400',
      bgGlow: 'rgba(234, 179, 8, 0.2)',
    },
    red: {
      stroke: '#ef4444',
      text: 'text-red-400',
      bgGlow: 'rgba(239, 68, 68, 0.2)',
    },
    cyan: {
      stroke: '#06b6d4',
      text: 'text-cyan-400',
      bgGlow: 'rgba(6, 182, 212, 0.2)',
    },
    multi: {
      stroke: percentage > 0.85 ? '#ef4444' : percentage > 0.6 ? '#eab308' : '#22c55e',
      text: percentage > 0.85 ? 'text-red-400' : percentage > 0.6 ? 'text-amber-400' : 'text-emerald-400',
      bgGlow: 'rgba(34, 197, 94, 0.15)',
    },
  };

  const scheme = colorMap[color] || colorMap.green;

  // Background arc path: M startX startY A radius radius 0 0 1 endX endY
  const bgPath = `M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`;
  // Value arc path: M startX startY A radius radius 0 0 1 curX curY
  const valPath = percentage > 0 ? `M ${startX} ${startY} A ${radius} ${radius} 0 0 1 ${curX} ${curY}` : '';

  return (
    <div className="bg-[#12151e] border border-[#232736] rounded-xl p-3 flex flex-col items-center justify-between shadow-sm relative overflow-hidden group hover:border-[#353b52] transition-colors">
      {/* Title */}
      <div className="w-full text-center">
        <span className="text-[11px] font-mono tracking-wide text-slate-400 truncate block">
          {title}
        </span>
      </div>

      {/* SVG Arc Gauge */}
      <div className="relative w-[170px] h-[95px] flex items-center justify-center mt-1">
        <svg className="w-full h-full overflow-visible" viewBox="0 0 170 95">
          {/* Subtle outer reference track */}
          <path
            d={bgPath}
            fill="none"
            stroke="#1e2433"
            strokeWidth={strokeWidth}
            strokeLinecap="round"
          />

          {/* Active colored arc */}
          {valPath && (
            <path
              d={valPath}
              fill="none"
              stroke={scheme.stroke}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              className="transition-all duration-150 ease-out"
              style={{
                filter: `drop-shadow(0 0 6px ${scheme.bgGlow})`,
              }}
            />
          )}

          {/* Min & Max labels */}
          <text x={startX - 2} y={startY + 13} fill="#64748b" fontSize="8" fontFamily="monospace" textAnchor="middle">
            {min}
          </text>
          <text x={endX + 2} y={endY + 13} fill="#64748b" fontSize="8" fontFamily="monospace" textAnchor="middle">
            {max}
          </text>
        </svg>

        {/* Value overlay positioned inside the semicircular arc */}
        <div className="absolute inset-x-0 bottom-1 flex flex-col items-center justify-center pointer-events-none">
          <span className={`text-base font-black font-mono tracking-tight leading-none ${scheme.text}`}>
            {value.toFixed(decimals)} <span className="text-[10px] text-slate-400 font-normal">{unit}</span>
          </span>
        </div>
      </div>
    </div>
  );
}
