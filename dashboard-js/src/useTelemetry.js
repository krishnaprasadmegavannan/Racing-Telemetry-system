// src/useTelemetry.js
import { useState, useEffect, useRef, useCallback } from 'react';
import fastf1TrackData from './assets/monza_fastf1_track.json';

const FALLBACK_TELEMETRY = fastf1TrackData?.telemetry || [];

function roundDec(val, dec = 2) {
  return Number(Number(val).toFixed(dec));
}

// ── Timing helpers ────────────────────────────────────────────────────────────
function msToLapString(ms) {
  if (!ms || ms <= 0) return '--:--.---';
  const totalSec = Math.floor(ms / 1000);
  const min = Math.floor(totalSec / 60);
  const sec = totalSec % 60;
  const mil = ms % 1000;
  return `${min}:${String(sec).padStart(2, '0')}.${String(mil).padStart(3, '0')}`;
}

function msToSectorString(ms) {
  if (!ms || ms <= 0) return '--.---s';
  return `${(ms / 1000).toFixed(3)}s`;
}

function msToDeltaString(ms) {
  if (ms === null || ms === undefined) return '';
  if (ms === 0) return '±0.000';
  const sign = ms > 0 ? '+' : '-';
  const abs = Math.abs(ms);
  return `${sign}${(abs / 1000).toFixed(3)}`;
}

// ── Realistic presets for HOTLAP vs ENDURANCE modes ──────────────────────────
export const MODE_PRESETS = {
  HOTLAP: {
    name: 'HOTLAP',
    description: 'Q3 Qualifying Push Lap (12 kg fuel, Soft C4 Tyres, Max Power)',
    baseMs: 80161,
    formatted: '1:20.161',
    driver: 'Charles Leclerc (Q3 Qualifying Pole)',
    compound: 'SOFT (C4)',
    fuelKg: 12.0,
    s1Ms: 27412,
    s2Ms: 37224,
    s3Ms: 15525,
    s1Str: '27.412s',
    s2Str: '37.224s',
    s3Str: '15.525s',
    deltas: [0, 324, 112, -215, 489, 720, -80, 250, -290, 510],
  },
  ENDURANCE: {
    name: 'ENDURANCE',
    description: 'Race Stint Run (105 kg fuel, Medium C3 Tyres, Race Pace)',
    baseMs: 84230,
    formatted: '1:24.230',
    driver: 'Charles Leclerc (Race Stint - High Fuel)',
    compound: 'MEDIUM (C3)',
    fuelKg: 105.0,
    s1Ms: 28640,
    s2Ms: 39180,
    s3Ms: 16410,
    s1Str: '28.640s',
    s2Str: '39.180s',
    s3Str: '16.410s',
    deltas: [0, 485, 250, -340, 390, 920, 80, 660, -490, 1190],
  },
};

function getSimulatedLapMs(lapNum, mode = 'HOTLAP') {
  const preset = MODE_PRESETS[mode.toUpperCase()] || MODE_PRESETS.HOTLAP;
  const delta = preset.deltas[(lapNum - 1) % preset.deltas.length];
  return preset.baseMs + delta;
}

// Monza reference sector boundaries (% of lap distance)
const SECTOR_THRESHOLDS = [0.333, 0.666]; // S1 ends at 33.3%, S2 at 66.6%

export function useTelemetry(url, mode = 'HOTLAP') {
  const activeMode = (mode || 'HOTLAP').toUpperCase();
  const activePreset = MODE_PRESETS[activeMode] || MODE_PRESETS.HOTLAP;

  const defaultBase = `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/telemetry/ws`;
  const baseWs = url || defaultBase;
  const wsUrl = baseWs.includes('?') ? `${baseWs}&mode=${activeMode}` : `${baseWs}?mode=${activeMode}`;

  const [data, setData]           = useState(null);
  const [history, setHistory]     = useState([]);
  const [alerts, setAlerts]       = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStale, setIsStale]     = useState(false);
  const [stats, setStats]         = useState({
    speedMin: 0, speedMax: 0, speedAvg: 0,
    rpmMin: 0,   rpmMax: 0,   rpmAvg: 0,
    speedTrap: 350.0,
  });

  // ── Lap timing state (exposed to UI) ─────────────────────────────────────────
  const [lapTiming, setLapTiming] = useState({
    currentLap: 2,
    currentLapMs: 0,            // ticking live clock
    currentLapFormatted: '0:00.000',
    fastestLapMs: activePreset.baseMs,
    fastestLapFormatted: activePreset.formatted,
    fastestLapNumber: 1,
    fastestDriver: activePreset.driver,
    lastLapMs: null,
    lastLapFormatted: '--:--.---',
    lastLapDelta: '',
    lapHistory: [
      {
        lap: 1,
        ms: activePreset.baseMs,
        formatted: activePreset.formatted,
        delta: 'PURPLE',
        deltaMs: 0,
        isPurple: true,
        s1Formatted: activePreset.s1Str,
        s2Formatted: activePreset.s2Str,
        s3Formatted: activePreset.s3Str,
      }
    ],
    // Current sector progress
    sector1Ms: null,
    sector2Ms: null,
    sector3Ms: null,
    currentSectorMs: 0,
    activeSector: 1,
    // Fastest lap sector splits
    fastestSector1Ms: activePreset.s1Ms,
    fastestSector2Ms: activePreset.s2Ms,
    fastestSector3Ms: activePreset.s3Ms,
    fastestSector1Formatted: activePreset.s1Str,
    fastestSector2Formatted: activePreset.s2Str,
    fastestSector3Formatted: activePreset.s3Str,
    // Mode parameters
    mode: activeMode,
    targetLapMs: activePreset.baseMs,
    targetLapFormatted: activePreset.formatted,
    compound: activePreset.compound,
    fuelKg: activePreset.fuelKg,
  });

  // ── Internal refs (don't trigger render) ────────────────────────────────────
  const lastValidFrame   = useRef(null);
  const staleTimer       = useRef(null);
  const maxSpeedEver     = useRef(350.0);
  const lapClockTimer    = useRef(null);
  const lastHardwarePacketMs = useRef(0);
  const lastExternalPacketMs = useRef(0);

  // Lap state refs
  const lapStartWallMs   = useRef(Date.now());
  const lapNumber        = useRef(2);
  const fastestLapMs     = useRef(activePreset.baseMs);
  const fastestLapNum    = useRef(1);
  const lastLapMs        = useRef(null);
  const lapHistory       = useRef([
    {
      lap: 1,
      ms: activePreset.baseMs,
      formatted: activePreset.formatted,
      delta: 'PURPLE',
      deltaMs: 0,
      isPurple: true,
      s1Formatted: activePreset.s1Str,
      s2Formatted: activePreset.s2Str,
      s3Formatted: activePreset.s3Str,
    }
  ]);

  // Sector refs
  const sector1EndMs     = useRef(null);
  const sector2EndMs     = useRef(null);
  const activeSector     = useRef(1);

  // Fastest lap sector bests
  const fastestS1        = useRef(activePreset.s1Ms);
  const fastestS2        = useRef(activePreset.s2Ms);
  const fastestS3        = useRef(activePreset.s3Ms);

  // Last known progress (0.0 – 1.0)
  const lastProgress     = useRef(0);

  // ── Synchronize state when activeMode changes (HOTLAP vs ENDURANCE) ──────────
  useEffect(() => {
    const curPreset = MODE_PRESETS[activeMode] || MODE_PRESETS.HOTLAP;
    fastestLapMs.current = curPreset.baseMs;
    fastestLapNum.current = 1;
    fastestS1.current = curPreset.s1Ms;
    fastestS2.current = curPreset.s2Ms;
    fastestS3.current = curPreset.s3Ms;
    lastLapMs.current = null;
    lapNumber.current = 2;
    lapStartWallMs.current = Date.now();
    sector1EndMs.current = null;
    sector2EndMs.current = null;
    activeSector.current = 1;
    lastProgress.current = 0;

    const initialHistory = [
      {
        lap: 1,
        ms: curPreset.baseMs,
        formatted: curPreset.formatted,
        delta: 'PURPLE',
        deltaMs: 0,
        isPurple: true,
        s1Formatted: curPreset.s1Str,
        s2Formatted: curPreset.s2Str,
        s3Formatted: curPreset.s3Str,
      }
    ];
    lapHistory.current = initialHistory;

    setLapTiming({
      currentLap: 2,
      currentLapMs: 0,
      currentLapFormatted: '0:00.000',
      fastestLapMs: curPreset.baseMs,
      fastestLapFormatted: curPreset.formatted,
      fastestLapNumber: 1,
      fastestDriver: curPreset.driver,
      lastLapMs: null,
      lastLapFormatted: '--:--.---',
      lastLapDelta: '',
      lapHistory: initialHistory,
      sector1Ms: null,
      sector2Ms: null,
      sector3Ms: null,
      currentSectorMs: 0,
      activeSector: 1,
      fastestSector1Ms: curPreset.s1Ms,
      fastestSector2Ms: curPreset.s2Ms,
      fastestSector3Ms: curPreset.s3Ms,
      fastestSector1Formatted: curPreset.s1Str,
      fastestSector2Formatted: curPreset.s2Str,
      fastestSector3Formatted: curPreset.s3Str,
      mode: activeMode,
      targetLapMs: curPreset.baseMs,
      targetLapFormatted: curPreset.formatted,
      compound: curPreset.compound,
      fuelKg: curPreset.fuelKg,
    });
  }, [activeMode]);

  // ── Live lap clock (10 Hz tick) ──────────────────────────────────────────────
  useEffect(() => {
    lapClockTimer.current = setInterval(() => {
      const now = Date.now();
      const lapElapsed = now - lapStartWallMs.current;

      // Sector elapsed since active sector start
      const sectorStart = activeSector.current === 1
        ? lapStartWallMs.current
        : activeSector.current === 2
          ? (sector1EndMs.current ?? lapStartWallMs.current)
          : (sector2EndMs.current ?? lapStartWallMs.current);

      const sectorElapsed = Math.max(0, now - sectorStart);

      setLapTiming(prev => ({
        ...prev,
        currentLap: lapNumber.current,
        currentLapMs: lapElapsed,
        currentLapFormatted: msToLapString(lapElapsed),
        currentSectorMs: sectorElapsed,
        activeSector: activeSector.current,
        sector1Ms: sector1EndMs.current
          ? Math.max(0, sector1EndMs.current - lapStartWallMs.current)
          : null,
        sector2Ms: (sector2EndMs.current && sector1EndMs.current)
          ? Math.max(0, sector2EndMs.current - sector1EndMs.current)
          : null,
      }));
    }, 100);

    return () => clearInterval(lapClockTimer.current);
  }, []);

  // ── Lap completion ────────────────────────────────────────────────────────────
  const completeLap = useCallback((lapTimeMs, lapNum, compData = null) => {
    const curPreset = MODE_PRESETS[activeMode] || MODE_PRESETS.HOTLAP;
    const now = Date.now();
    const effectiveLapMs = lapTimeMs && lapTimeMs > 10000 
      ? lapTimeMs 
      : Math.max(curPreset.baseMs - 5000, now - lapStartWallMs.current);

    let s1 = compData?.s1 ? Math.round(compData.s1 * 1000) : (sector1EndMs.current ? sector1EndMs.current - lapStartWallMs.current : null);
    let s2 = compData?.s2 ? Math.round(compData.s2 * 1000) : (sector2EndMs.current && sector1EndMs.current ? sector2EndMs.current - sector1EndMs.current : null);
    let s3 = compData?.s3 ? Math.round(compData.s3 * 1000) : (s1 && s2 ? effectiveLapMs - s1 - s2 : null);

    if (!s1 || !s2 || !s3 || s1 <= 0 || s2 <= 0 || s3 <= 0) {
      const s1Ratio = curPreset.s1Ms / curPreset.baseMs;
      const s2Ratio = curPreset.s2Ms / curPreset.baseMs;
      s1 = Math.round(effectiveLapMs * s1Ratio);
      s2 = Math.round(effectiveLapMs * s2Ratio);
      s3 = Math.round(effectiveLapMs - s1 - s2);
    }

    const isPurple = effectiveLapMs < fastestLapMs.current;
    if (isPurple) {
      fastestLapMs.current  = effectiveLapMs;
      fastestLapNum.current = lapNum;
      fastestS1.current     = s1;
      fastestS2.current     = s2;
      fastestS3.current     = s3;
    }

    const delta = effectiveLapMs - fastestLapMs.current;

    const entry = {
      lap: lapNum,
      ms: effectiveLapMs,
      formatted: msToLapString(effectiveLapMs),
      delta: isPurple ? 'PURPLE' : msToDeltaString(delta),
      deltaMs: delta,
      isPurple,
      s1Formatted: msToSectorString(s1),
      s2Formatted: msToSectorString(s2),
      s3Formatted: msToSectorString(s3),
    };

    lapHistory.current = [entry, ...lapHistory.current.filter(l => l.lap !== lapNum)].slice(0, 15);
    lastLapMs.current  = effectiveLapMs;
    lapNumber.current  = lapNum + 1;

    // Reset lap clock for new lap
    lapStartWallMs.current = Date.now();
    sector1EndMs.current   = null;
    sector2EndMs.current   = null;
    activeSector.current   = 1;
    lastProgress.current   = 0;

    setLapTiming(prev => ({
      ...prev,
      currentLap: lapNum + 1,
      lastLapMs: effectiveLapMs,
      lastLapFormatted: msToLapString(effectiveLapMs),
      lastLapDelta: isPurple ? 'PURPLE' : msToDeltaString(delta),
      fastestLapMs: fastestLapMs.current,
      fastestLapFormatted: msToLapString(fastestLapMs.current),
      fastestLapNumber: fastestLapNum.current,
      lapHistory: [...lapHistory.current],
      fastestSector1Ms: fastestS1.current,
      fastestSector2Ms: fastestS2.current,
      fastestSector3Ms: fastestS3.current,
      fastestSector1Formatted: msToSectorString(fastestS1.current),
      fastestSector2Formatted: msToSectorString(fastestS2.current),
      fastestSector3Formatted: msToSectorString(fastestS3.current),
      sector1Ms: null,
      sector2Ms: null,
      sector3Ms: null,
      activeSector: 1,
    }));
  }, [activeMode]);

  // ── Sector detection from telemetry progress ──────────────────────────────────
  const checkSectorTransition = useCallback((progress) => {
    const prev = lastProgress.current;
    lastProgress.current = progress;

    const now = Date.now();

    // Sector 1 → 2 boundary
    if (activeSector.current === 1 && progress >= SECTOR_THRESHOLDS[0] && prev < SECTOR_THRESHOLDS[0]) {
      sector1EndMs.current = now;
      activeSector.current = 2;
    }
    // Sector 2 → 3 boundary
    if (activeSector.current === 2 && progress >= SECTOR_THRESHOLDS[1] && prev < SECTOR_THRESHOLDS[1]) {
      sector2EndMs.current = now;
      activeSector.current = 3;
    }
    // Sector 3 → Finish Line wrap-around (progress wraps from >0.80 to <0.15)
    if (activeSector.current === 3 && prev > 0.80 && progress < 0.15) {
      const curLap = lapNumber.current;
      const alreadyRecorded = lapHistory.current.some(l => l.lap === curLap);
      if (!alreadyRecorded) {
        const simMs = getSimulatedLapMs(curLap, activeMode);
        completeLap(simMs, curLap);
      }
    }
  }, [completeLap, activeMode]);

  // ── Unified Frame Ingestion ──────────────────────────────────────────────────
  const handleIngestedFrame = useCallback((message, isHardware = false) => {
    try {
      if (!(message.type === 'telemetry_update' || message.raw || message.speed)) return;

      const raw       = message.raw || message.data || message;
      const processed = message.processed || {};
      const gps       = raw.gps || {};
      const can       = raw.vehicle_can || raw.vehicle || {};
      const imu       = raw.imu || {};
      const temp      = raw.temperature || {};
      const wheels    = raw.wheel_speeds || {};
      const meta      = raw.metadata || {};
      const tyre      = raw.tyre_wear || {};

      const transmissionInfo = String(meta.transmission_information || raw.transmission_information || '');
      const isActualHardware = isHardware || transmissionInfo.includes('ESP32') || transmissionInfo.includes('HARDWARE');

      if (isActualHardware) {
        lastHardwarePacketMs.current = Date.now();
      }

      // Core values
      const speed = Math.max(0, Number(gps.speed ?? raw.speed ?? lastValidFrame.current?.speed ?? 0));
      if (speed > maxSpeedEver.current) maxSpeedEver.current = Math.round(speed * 100) / 100;

      // Correlate Throttle & Brake: strictly mutually exclusive
      const rawThrottle = Number(can.throttle ?? raw.throttle ?? 0);
      let throttle = Math.min(100, Math.max(0,
        rawThrottle <= 1.0 && rawThrottle > 0 ? rawThrottle * 100 : rawThrottle));

      const rawBrake = Number(can.brake_pressure ?? raw.brake_pressure ?? 0);
      let brake_pressure = Math.min(100, Math.max(0,
        rawBrake <= 1.0 && rawBrake > 0 ? rawBrake * 100 : rawBrake));

      if (brake_pressure > 15) {
        throttle = 0;
      } else if (throttle > 15) {
        brake_pressure = 0;
      }

      // Correlate Gear with Speed
      const expectedGear = (
        speed < 75 ? 1 :
        speed < 115 ? 2 :
        speed < 155 ? 3 :
        speed < 195 ? 4 :
        speed < 240 ? 5 :
        speed < 285 ? 6 :
        speed < 320 ? 7 : 8
      );
      const rawGear = Number(can.gear ?? raw.gear ?? 0);
      const gear = (rawGear > 0 && Math.abs(rawGear - expectedGear) <= 1) ? rawGear : expectedGear;

      // Correlate RPM with Gear and Speed (8,500 - 12,500 rpm for F1 turbo hybrid)
      let rawRpm = Number(can.rpm ?? raw.rpm ?? 0);
      let rpm = rawRpm;
      if (speed > 80 && (rawRpm < 7500 || rawRpm > 14000)) {
        rpm = Math.min(12500, Math.max(8800, 8500 + Math.round((speed % 40) * 85)));
      } else if (speed <= 80 && rawRpm === 0) {
        rpm = Math.max(4500, Math.round(speed * 60));
      }

      // Correlate G-forces with braking/acceleration and cornering
      let ax = Number(processed.longitudinal_acceleration ?? imu.ax ?? 0);
      let ay = Number(processed.lateral_acceleration      ?? imu.ay ?? 0);
      let az = Number(processed.vertical_acceleration     ?? imu.az ?? 9.81);

      let long_g = Number(processed.long_g ?? (ax / 9.81));
      if (brake_pressure > 15 && long_g > -0.5) {
        long_g = -Number(Math.min(5.2, brake_pressure / 21.0).toFixed(2));
        ax = Number((long_g * 9.81).toFixed(2));
      } else if (throttle > 50 && long_g < 0.2) {
        long_g = Number((throttle / 65.0).toFixed(2));
        ax = Number((long_g * 9.81).toFixed(2));
      }

      let lat_g = Number(processed.lat_g ?? (ay / 9.81));
      const resultantG = Number((Math.sqrt(ax * ax + ay * ay + az * az) / 9.81).toFixed(2));
      const corneringIntensity = Math.min(100, Math.round((Math.abs(lat_g) / 4.5) * 100));

      const battery_voltage = Number(can.battery_voltage ?? lastValidFrame.current?.battery_voltage ?? 14.2);
      const battery_current = Number(can.battery_current ?? lastValidFrame.current?.battery_current ?? (2.5 + (throttle / 100) * 1.5));
      const powerKW = Number(((battery_voltage * battery_current) / 1000).toFixed(2));

      // Correlate wheel speeds with speed and slip
      const wheel_fl = Number(wheels.front_left  ?? speed);
      const wheel_fr = Number(wheels.front_right ?? speed);
      const wheel_rl = Number(wheels.rear_left   ?? (throttle > 85 ? speed + 1.2 : speed));
      const wheel_rr = Number(wheels.rear_right  ?? (throttle > 85 ? speed + 1.2 : speed));
      const drivenWheels  = Math.max(wheel_rl, wheel_rr);
      const rollingWheels = Math.min(wheel_fl, wheel_fr);
      const wheelSlipDelta = Number(Math.max(0, drivenWheels - rollingWheels).toFixed(1));

      // Correlate brake temps
      const brake_temp_fl = Number(temp.brake_temp_fl ?? (650 + (brake_pressure / 100) * 350));
      const brake_temp_fr = Number(temp.brake_temp_fr ?? (648 + (brake_pressure / 100) * 350));
      const brake_temp_rl = Number(temp.brake_temp_rl ?? (610 + (brake_pressure / 100) * 280));
      const brake_temp_rr = Number(temp.brake_temp_rr ?? (608 + (brake_pressure / 100) * 280));

      const tyre_wear_fl = Number(tyre.fl ?? 13.0);
      const tyre_wear_fr = Number(tyre.fr ?? 11.0);
      const tyre_wear_rl = Number(tyre.rl ?? 11.0);
      const tyre_wear_rr = Number(tyre.rr ?? 10.0);

      const curPreset = MODE_PRESETS[activeMode] || MODE_PRESETS.HOTLAP;
      const rawProgress = Number(raw.progress ?? 0);
      const progress = rawProgress > 0 
        ? rawProgress 
        : (((Date.now() - lapStartWallMs.current) % curPreset.baseMs) / curPreset.baseMs);

      // Sector boundary detection
      checkSectorTransition(progress);

      // Lap completion handling
      if (message.lap_completed) {
        const comp = message.lap_completed;
        const alreadyRecorded = lapHistory.current.some(l => l.lap === comp.lap_number);
        if (!alreadyRecorded) {
          completeLap(comp.lap_time_ms, comp.lap_number, comp);
        }
      } else if (message.lap && message.lap.lap_completed) {
        const comp = message.lap.lap_completed;
        const alreadyRecorded = lapHistory.current.some(l => l.lap === comp.lap_number);
        if (!alreadyRecorded) {
          completeLap(comp.lap_time_ms, comp.lap_number, comp);
        }
      } else if (message.lap && message.lap.lap_time && message.lap.lap_number && message.lap.lap_number >= lapNumber.current) {
        const backendLapMs  = Math.round(message.lap.lap_time * 1000);
        const backendLapNum = message.lap.lap_number;
        const alreadyRecorded = lapHistory.current.some(l => l.lap === backendLapNum);
        if (!alreadyRecorded && backendLapMs > 5000) {
          completeLap(backendLapMs, backendLapNum);
        }
      }

      // Mode-specific channels
      const fuel_kg = Number(raw.fuel_kg ?? message.fuel_kg ?? (activeMode === 'ENDURANCE' ? 104.5 : 11.8));
      const tyre_compound = String(raw.tyre_compound ?? message.tyre_compound ?? curPreset.compound);
      const ers_mode = String(raw.ers_mode ?? message.ers_mode ?? (activeMode === 'ENDURANCE' ? 'RACE BALANCED' : 'HOTLAP QUALIFYING'));

      // Frame construction
      const newPoint = {
        latitude:  Number(gps.latitude  ?? 45.618),
        longitude: Number(gps.longitude ?? 9.281),
        altitude:  Number(gps.altitude  ?? 183.0),
        satellite_count: Number(gps.satellite_count ?? 14),
        fix_status: String(gps.fix_status ?? '3D_FIX'),

        speed, rpm, gear, throttle, brake_pressure,
        ax, ay, az, resultantG, corneringIntensity,
        gx: Number(imu.gx ?? 0),
        gy: Number(imu.gy ?? 0),
        gz: Number(imu.gz ?? 0),

        wheel_fl, wheel_fr, wheel_rl, wheel_rr, wheelSlipDelta,

        coolant_temp:  Number(temp.coolant_temperature ?? 92.5),
        engine_temp:   Number(temp.engine_temperature  ?? 105.0),
        brake_temp_fl, brake_temp_fr, brake_temp_rl, brake_temp_rr,

        tyre_wear_fl, tyre_wear_fr, tyre_wear_rl, tyre_wear_rr,
        tyre_age_lap:   Number(tyre.age_lap ?? lapNumber.current),
        engine_damage: 10.0,

        battery_voltage, battery_current, powerKW,
        speedTrap: maxSpeedEver.current,

        track_x:     Number(raw.track_x ?? gps.track_x ?? 741.6),
        track_y:     Number(raw.track_y ?? gps.track_y ?? 473.2),
        progress,
        corner_name: String(raw.corner_name || processed.corner_name || 'Main Straight'),
        sector:      Number(raw.sector || activeSector.current || 1),
        distance:    Number(raw.distance || 0),
        drs:         Number(can.drs ?? raw.drs ?? 0),
        long_g:      Number(processed.long_g ?? (ax / 9.81)),
        lat_g:       Number(processed.lat_g  ?? (ay / 9.81)),

        fuel_kg,
        tyre_compound,
        ers_mode,
        telemetry_mode: activeMode,

        timestamp:            Number(meta.timestamp        ?? Date.now() / 1000),
        sequence_number:      Number(meta.sequence_number  ?? 0),
        sampling_rate:        Number(meta.sampling_rate    ?? 50),
        status_error_information:  String(meta.status_error_information  ?? 'OK'),
        transmission_information:  isActualHardware
          ? (transmissionInfo.includes('ESP32') ? transmissionInfo : 'ESP32_SERIAL_CAN')
          : 'FastF1 Telemetry (Monza)',
      };

      lastValidFrame.current = newPoint;
      setData(newPoint);
      setIsConnected(true);
      setIsStale(false);

      if (staleTimer.current) clearTimeout(staleTimer.current);
      staleTimer.current = setTimeout(() => setIsStale(true), 2500);

      // Rolling history
      setHistory((prev) => {
        const next = [...prev, newPoint];
        const trimmed = next.length > 150 ? next.slice(-150) : next;
        if (trimmed.length > 0) {
          let sMin = Infinity, sMax = -Infinity, sSum = 0;
          let rMin = Infinity, rMax = -Infinity, rSum = 0;
          for (const pt of trimmed) {
            if (pt.speed < sMin) sMin = pt.speed;
            if (pt.speed > sMax) sMax = pt.speed;
            sSum += pt.speed;
            if (pt.rpm < rMin) rMin = pt.rpm;
            if (pt.rpm > rMax) rMax = pt.rpm;
            rSum += pt.rpm;
          }
          setStats({
            speedMin: Math.round(sMin),
            speedMax: Math.round(sMax),
            speedAvg: Math.round(sSum / trimmed.length),
            rpmMin: Math.round(rMin),
            rpmMax: Math.round(rMax),
            rpmAvg: Math.round(rSum / trimmed.length),
            speedTrap: maxSpeedEver.current,
          });
        }
        return trimmed;
      });

      // Alerts — one active at a time
      if (message.alerts && Array.isArray(message.alerts) && message.alerts.length > 0) {
        const active = message.alerts[0];
        setAlerts([{
          id: active.id || 'active-alert',
          level: (active.severity || 'warning').toLowerCase(),
          alert_type: active.alert_type || 'TELEMETRY EVENT',
          message: active.message || active.alert_type || 'System Anomaly',
          time: new Date().toLocaleTimeString(),
        }]);
      } else if (message.alerts && Array.isArray(message.alerts) && message.alerts.length === 0) {
        setAlerts([]);
      }
    } catch (e) {
      console.error('Frame ingestion error:', e);
    }
  }, [activeMode, checkSectorTransition, completeLap]);

  // ── Default / Fallback FastF1 Playback Loop ──────────────────────────────────
  useEffect(() => {
    if (!FALLBACK_TELEMETRY.length) return;

    let simIdx = 0;
    let simLapNumber = 1;
    const intervalMs = activeMode === 'ENDURANCE' ? 135 : 125;

    const simTimer = setInterval(() => {
      // If ANY external WebSocket packets arrived within the last 2.0s, yield to external stream
      if (Date.now() - lastExternalPacketMs.current < 2000) {
        return;
      }

      const frame = FALLBACK_TELEMETRY[simIdx];
      if (!frame) return;

      const isEndurance = (activeMode === 'ENDURANCE');

      // Mode physics scaling
      let speed_adj, rpm_adj, fuel_kg, tyre_compound, ers_mode, tyre_fl, tyre_fr, tyre_rl, tyre_rr;

      if (isEndurance) {
        speed_adj = roundDec(frame.speed * 0.965, 1);
        rpm_adj = Math.min(18200, Math.round(frame.rpm * 0.97));
        fuel_kg = Math.max(15.0, roundDec(105.0 - (simLapNumber - 1) * 1.85 - (frame.progress * 1.85), 2));
        tyre_compound = 'MEDIUM (C3)';
        ers_mode = 'RACE BALANCED (HARVEST/DEPLOY)';
        tyre_fl = roundDec(15.0 + simLapNumber * 1.4, 1);
        tyre_fr = roundDec(13.0 + simLapNumber * 1.1, 1);
        tyre_rl = roundDec(12.5 + simLapNumber * 1.3, 1);
        tyre_rr = roundDec(11.8 + simLapNumber * 1.0, 1);
      } else {
        speed_adj = frame.speed;
        rpm_adj = frame.rpm;
        fuel_kg = Math.max(2.5, roundDec(12.0 - (simLapNumber - 1) * 2.2 - (frame.progress * 2.2), 2));
        tyre_compound = 'SOFT (C4)';
        ers_mode = 'HOTLAP QUALIFYING DEPLOY (100%)';
        tyre_fl = roundDec(13.0 + simLapNumber * 2.5, 1);
        tyre_fr = roundDec(11.0 + simLapNumber * 2.0, 1);
        tyre_rl = roundDec(11.0 + simLapNumber * 2.2, 1);
        tyre_rr = roundDec(10.0 + simLapNumber * 1.8, 1);
      }

      // Check lap completion on wrap-around
      let lapCompleted = null;
      if (simIdx === 0 && simLapNumber > 1) {
        const prevLap = simLapNumber - 1;
        const curPreset = MODE_PRESETS[activeMode] || MODE_PRESETS.HOTLAP;
        const delta = curPreset.deltas[(prevLap - 1) % curPreset.deltas.length];
        const lapTimeMs = curPreset.baseMs + delta;
        lapCompleted = {
          lap_number: prevLap,
          lap_time_ms: lapTimeMs,
          lap_time: lapTimeMs / 1000,
          s1: Math.round(curPreset.s1Ms + (delta * 0.35)) / 1000,
          s2: Math.round(curPreset.s2Ms + (delta * 0.45)) / 1000,
          s3: Math.round(lapTimeMs - (curPreset.s1Ms + (delta * 0.35)) - (curPreset.s2Ms + (delta * 0.45))) / 1000,
        };
      }

      const alerts = [];
      if (frame.brake_pressure > 80) {
        alerts.push({
          id: 'heavy_braking_zone',
          severity: 'warning',
          alert_type: 'HEAVY BRAKING ZONE',
          message: `Threshold decel ${(frame.long_g || 0).toFixed(1)}G into ${frame.corner_name || 'Turn'}`,
        });
      } else if (speed_adj > 330 && frame.drs > 0) {
        alerts.push({
          id: 'speed_trap_active',
          severity: 'info',
          alert_type: 'DRS HIGH SPEED TRAP',
          message: `VMAX ${speed_adj.toFixed(0)} km/h - DRS Active on Rettifilo`,
        });
      }

      const syntheticPacket = {
        type: 'telemetry_update',
        timestamp: Date.now() / 1000,
        telemetry_mode: activeMode,
        fuel_kg,
        tyre_compound,
        ers_mode,
        lap_completed: lapCompleted,
        raw: {
          gps: {
            latitude: frame.latitude,
            longitude: frame.longitude,
            altitude: 183.0,
            speed: speed_adj,
            satellite_count: 14,
            fix_status: '3D_FIX',
            track_x: frame.track_x,
            track_y: frame.track_y,
          },
          vehicle_can: {
            rpm: rpm_adj,
            gear: frame.gear,
            throttle: frame.throttle,
            brake_pressure: frame.brake_pressure,
            battery_voltage: 14.2,
            battery_current: isEndurance ? roundDec(2.0 + (frame.throttle / 100) * 1.5, 2) : 2.5,
            drs: frame.drs,
          },
          imu: {
            ax: frame.ax,
            ay: frame.ay,
            az: 9.81,
            gx: 0.0,
            gy: 0.0,
            gz: roundDec((frame.lat_g || 0) * 0.12, 3),
          },
          temperature: {
            coolant_temperature: frame.coolant_temp,
            engine_temperature: frame.engine_temp,
            brake_temp_fl: frame.brake_temp_fl,
            brake_temp_fr: frame.brake_temp_fr,
            brake_temp_rl: frame.brake_temp_rl,
            brake_temp_rr: frame.brake_temp_rr,
          },
          wheel_speeds: {
            front_left: speed_adj,
            front_right: speed_adj,
            rear_left: speed_adj,
            rear_right: speed_adj,
          },
          tyre_wear: {
            fl: tyre_fl,
            fr: tyre_fr,
            rl: tyre_rl,
            rr: tyre_rr,
            age_lap: simLapNumber,
          },
          metadata: {
            timestamp: Date.now() / 1000,
            sequence_number: simIdx,
            sampling_rate: isEndurance ? 8 : 10,
            status_error_information: 'OK',
            transmission_information: 'FastF1 Telemetry (Monza)',
          },
          track_x: frame.track_x,
          track_y: frame.track_y,
          speed: speed_adj,
          rpm: rpm_adj,
          gear: frame.gear,
          throttle: frame.throttle,
          brake_pressure: frame.brake_pressure,
          corner_name: frame.corner_name,
          sector: frame.sector,
          distance: frame.distance_m,
          progress: frame.progress,
          fuel_kg,
          tyre_compound,
          ers_mode,
        },
        processed: {
          longitudinal_acceleration: frame.ax,
          lateral_acceleration: frame.ay,
          vertical_acceleration: 9.81,
          long_g: frame.long_g,
          lat_g: frame.lat_g,
          resultant_g: frame.resultant_g,
          cornering_intensity: frame.cornering_intensity,
          braking_intensity: frame.brake_pressure,
          corner_name: frame.corner_name,
        },
        alerts,
      };

      handleIngestedFrame(syntheticPacket, false);

      simIdx += 1;
      if (simIdx >= FALLBACK_TELEMETRY.length) {
        simIdx = 0;
        simLapNumber += 1;
      }
    }, intervalMs);

    return () => clearInterval(simTimer);
  }, [activeMode, completeLap, handleIngestedFrame]);

  // ── WebSocket ────────────────────────────────────────────────────────────────
  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;

    function connect() {
      try {
        ws = new WebSocket(wsUrl);
      } catch (err) {
        console.error('WebSocket connection error:', err);
        scheduleReconnect();
        return;
      }

      ws.onopen = () => { setIsConnected(true); setIsStale(false); };
      ws.onclose = () => {
        // If WebSocket closes, do not mark as stale if local stream is active
        if (Date.now() - lastHardwarePacketMs.current >= 2500) {
          setIsConnected(true);
          setIsStale(false);
        }
        scheduleReconnect();
      };
      ws.onerror = (e) => console.error('WS error:', e);

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          lastExternalPacketMs.current = Date.now();
          const meta = message.raw?.metadata || message.metadata || {};
          const isHw = String(meta.transmission_information || message.transmission_information || '').includes('ESP32');
          handleIngestedFrame(message, isHw);
        } catch (e) {
          console.error('WS parse error:', e);
        }
      };
    }

    function scheduleReconnect() {
      if (!reconnectTimeout) {
        reconnectTimeout = setTimeout(() => {
          reconnectTimeout = null;
          connect();
        }, 2000);
      }
    }

    connect();
    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (staleTimer.current) clearTimeout(staleTimer.current);
    };
  }, [wsUrl, handleIngestedFrame]);

  return { data, history, stats, alerts, isConnected, isStale, setAlerts, lapTiming };
}