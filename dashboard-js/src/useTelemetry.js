// src/useTelemetry.js
import { useState, useEffect, useRef, useCallback } from 'react';
import fastf1TrackData from './assets/monza_fastf1_track.json';

const FALLBACK_TELEMETRY = fastf1TrackData?.telemetry || [];

function roundDec(val, dec = 2) {
  return Number(Number(val).toFixed(dec));
}

// ── Timing helpers ─────────────────────────────────────────────────────────────
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

// ── Single Monza Race Day preset ──────────────────────────────────────────────
export const PRESET = {
  baseMs: 84230,
  formatted: '1:24.230',
  driver: 'Charles Leclerc (#16 Ferrari F1-75)',
  compound: 'MEDIUM (C3)',
  fuelKg: 105.0,
  s1Ms: 28640,
  s2Ms: 39180,
  s3Ms: 16410,
  s1Str: '28.640s',
  s2Str: '39.180s',
  s3Str: '16.410s',
  // Realistic race stint deltas (ms) — tyre thermal progression & fuel burn-off
  deltas: [0, 485, 250, -340, 390, 920, 80, 660, -490, 1190],
};

function getSimulatedLapMs(lapNum) {
  const delta = PRESET.deltas[(lapNum - 1) % PRESET.deltas.length];
  return PRESET.baseMs + delta;
}

// Sector boundaries at 33.3% and 66.6% of lap
const SECTOR_THRESHOLDS = [0.333, 0.666];

// ── Linear interpolation for smoothed display values ──────────────────────────
function lerp(a, b, t) {
  return a + (b - a) * t;
}

export function useTelemetry(url) {
  const defaultBase = `${window.location.protocol.replace('http', 'ws')}//${window.location.host}/telemetry/ws`;
  const wsUrl = url || defaultBase;

  const [data, setData]           = useState(null);
  const [history, setHistory]     = useState([]);
  const [alerts, setAlerts]       = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStale, setIsStale]     = useState(false);
  const [stats, setStats]         = useState({
    speedMin: 73, speedMax: 343, speedAvg: 258,
    rpmMin: 6635, rpmMax: 12205, rpmAvg: 10450,
    speedTrap: 343.0,
  });

  // ── Lap timing state ──────────────────────────────────────────────────────────
  const [lapTiming, setLapTiming] = useState({
    currentLap: 2,
    currentLapMs: 0,
    currentLapFormatted: '0:00.000',
    fastestLapMs: PRESET.baseMs,
    fastestLapFormatted: PRESET.formatted,
    fastestLapNumber: 1,
    fastestDriver: PRESET.driver,
    lastLapMs: null,
    lastLapFormatted: '--:--.---',
    lastLapDelta: '',
    lapHistory: [{
      lap: 1,
      ms: PRESET.baseMs,
      formatted: PRESET.formatted,
      delta: 'PURPLE',
      deltaMs: 0,
      isPurple: true,
      s1Formatted: PRESET.s1Str,
      s2Formatted: PRESET.s2Str,
      s3Formatted: PRESET.s3Str,
    }],
    sector1Ms: null,
    sector2Ms: null,
    sector3Ms: null,
    currentSectorMs: 0,
    activeSector: 1,
    fastestSector1Ms: PRESET.s1Ms,
    fastestSector2Ms: PRESET.s2Ms,
    fastestSector3Ms: PRESET.s3Ms,
    fastestSector1Formatted: PRESET.s1Str,
    fastestSector2Formatted: PRESET.s2Str,
    fastestSector3Formatted: PRESET.s3Str,
    compound: PRESET.compound,
    fuelKg: PRESET.fuelKg,
  });

  // ── Internal refs ──────────────────────────────────────────────────────────────
  const lastValidFrame       = useRef(null);
  const smoothedFrame        = useRef(null);    // holds lerp-smoothed display values
  const staleTimer           = useRef(null);
  const maxSpeedEver         = useRef(343.0);
  const lapClockTimer        = useRef(null);
  const lastHardwarePacketMs = useRef(0);
  const lastExternalPacketMs = useRef(0);

  // Lap state refs
  const lapStartWallMs   = useRef(Date.now());
  const lapNumber        = useRef(2);
  const fastestLapMs     = useRef(PRESET.baseMs);
  const fastestLapNum    = useRef(1);
  const lastLapMs        = useRef(null);
  const lapHistory       = useRef([{
    lap: 1,
    ms: PRESET.baseMs,
    formatted: PRESET.formatted,
    delta: 'PURPLE',
    deltaMs: 0,
    isPurple: true,
    s1Formatted: PRESET.s1Str,
    s2Formatted: PRESET.s2Str,
    s3Formatted: PRESET.s3Str,
  }]);

  // Sector refs
  const sector1EndMs     = useRef(null);
  const sector2EndMs     = useRef(null);
  const activeSector     = useRef(1);

  // Fastest lap sector bests
  const fastestS1        = useRef(PRESET.s1Ms);
  const fastestS2        = useRef(PRESET.s2Ms);
  const fastestS3        = useRef(PRESET.s3Ms);

  const lastProgress     = useRef(0);

  // ── Live lap clock (10 Hz tick) ────────────────────────────────────────────────
  useEffect(() => {
    lapClockTimer.current = setInterval(() => {
      const now = Date.now();
      const lapElapsed = now - lapStartWallMs.current;
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

  // ── Lap completion ──────────────────────────────────────────────────────────────
  const completeLap = useCallback((lapTimeMs, lapNum, compData = null) => {
    const effectiveLapMs = lapTimeMs && lapTimeMs > 10000
      ? lapTimeMs
      : Math.max(PRESET.baseMs - 5000, Date.now() - lapStartWallMs.current);

    let s1 = compData?.s1 ? Math.round(compData.s1 * 1000) : (sector1EndMs.current ? sector1EndMs.current - lapStartWallMs.current : null);
    let s2 = compData?.s2 ? Math.round(compData.s2 * 1000) : (sector2EndMs.current && sector1EndMs.current ? sector2EndMs.current - sector1EndMs.current : null);
    let s3 = compData?.s3 ? Math.round(compData.s3 * 1000) : (s1 && s2 ? effectiveLapMs - s1 - s2 : null);

    if (!s1 || !s2 || !s3 || s1 <= 0 || s2 <= 0 || s3 <= 0) {
      s1 = Math.round(effectiveLapMs * (PRESET.s1Ms / PRESET.baseMs));
      s2 = Math.round(effectiveLapMs * (PRESET.s2Ms / PRESET.baseMs));
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
    }));
  }, []);

  // ── Sector detection ───────────────────────────────────────────────────────────
  const checkSectorTransition = useCallback((progress) => {
    const prev = lastProgress.current;
    lastProgress.current = progress;
    const now = Date.now();

    if (activeSector.current === 1 && progress >= SECTOR_THRESHOLDS[0] && prev < SECTOR_THRESHOLDS[0]) {
      sector1EndMs.current = now;
      activeSector.current = 2;
    }
    if (activeSector.current === 2 && progress >= SECTOR_THRESHOLDS[1] && prev < SECTOR_THRESHOLDS[1]) {
      sector2EndMs.current = now;
      activeSector.current = 3;
    }
    if (activeSector.current === 3 && prev > 0.80 && progress < 0.15) {
      const curLap = lapNumber.current;
      const alreadyRecorded = lapHistory.current.some(l => l.lap === curLap);
      if (!alreadyRecorded) {
        completeLap(getSimulatedLapMs(curLap), curLap);
      }
    }
  }, [completeLap]);

  // ── Frame ingestion with lerp smoothing ──────────────────────────────────────
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

      if (isActualHardware) lastHardwarePacketMs.current = Date.now();

      // ── Raw physics ──────────────────────────────────────────────────────────
      const speed = Math.max(0, Number(gps.speed ?? raw.speed ?? lastValidFrame.current?.speed ?? 0));
      if (speed > maxSpeedEver.current) maxSpeedEver.current = Math.round(speed * 100) / 100;

      const rawThrottle = Number(can.throttle ?? raw.throttle ?? 0);
      let throttle = Math.min(100, Math.max(0,
        rawThrottle <= 1.0 && rawThrottle > 0 ? rawThrottle * 100 : rawThrottle));
      const rawBrake = Number(can.brake_pressure ?? raw.brake_pressure ?? 0);
      let brake_pressure = Math.min(100, Math.max(0,
        rawBrake <= 1.0 && rawBrake > 0 ? rawBrake * 100 : rawBrake));

      if (brake_pressure > 15) throttle = 0;
      else if (throttle > 15) brake_pressure = 0;

      const expectedGear = (
        speed < 75 ? 1 : speed < 115 ? 2 : speed < 155 ? 3 :
        speed < 195 ? 4 : speed < 240 ? 5 : speed < 285 ? 6 :
        speed < 320 ? 7 : 8
      );
      const rawGear = Number(can.gear ?? raw.gear ?? 0);
      const gear = (rawGear > 0 && Math.abs(rawGear - expectedGear) <= 1) ? rawGear : expectedGear;

      let rawRpm = Number(can.rpm ?? raw.rpm ?? 0);
      let rpm = rawRpm > 0 ? rawRpm : Math.max(4500, Math.round(speed * 35));

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
      const battery_current = Number(can.battery_current ?? lastValidFrame.current?.battery_current ?? (2.2 + (throttle / 100) * 1.2));
      const powerKW = Number(((battery_voltage * battery_current) / 1000).toFixed(2));

      const wheel_fl = Number(wheels.front_left  ?? speed);
      const wheel_fr = Number(wheels.front_right ?? speed);
      const wheel_rl = Number(wheels.rear_left   ?? (throttle > 85 ? speed + 1.2 : speed));
      const wheel_rr = Number(wheels.rear_right  ?? (throttle > 85 ? speed + 1.2 : speed));
      const wheelSlipDelta = Number(Math.max(0, Math.max(wheel_rl, wheel_rr) - Math.min(wheel_fl, wheel_fr)).toFixed(1));

      const brake_temp_fl = Number(temp.brake_temp_fl ?? raw.brake_temp_fl ?? (520 + (brake_pressure / 100) * 520));
      const brake_temp_fr = Number(temp.brake_temp_fr ?? raw.brake_temp_fr ?? (518 + (brake_pressure / 100) * 520));
      const brake_temp_rl = Number(temp.brake_temp_rl ?? raw.brake_temp_rl ?? (470 + (brake_pressure / 100) * 440));
      const brake_temp_rr = Number(temp.brake_temp_rr ?? raw.brake_temp_rr ?? (468 + (brake_pressure / 100) * 440));

      const tyre_wear_fl = Number(tyre.fl ?? raw.tyre_fl ?? Math.min(100, 8.0 + (lapNumber.current - 1) * 2.2));
      const tyre_wear_fr = Number(tyre.fr ?? raw.tyre_fr ?? Math.min(100, 7.0 + (lapNumber.current - 1) * 1.9));
      const tyre_wear_rl = Number(tyre.rl ?? raw.tyre_rl ?? Math.min(100, 6.5 + (lapNumber.current - 1) * 1.8));
      const tyre_wear_rr = Number(tyre.rr ?? raw.tyre_rr ?? Math.min(100, 6.0 + (lapNumber.current - 1) * 1.7));

      const rawProgress = Number(raw.progress ?? 0);
      const progress = rawProgress > 0 ? rawProgress
        : (((Date.now() - lapStartWallMs.current) % PRESET.baseMs) / PRESET.baseMs);

      checkSectorTransition(progress);

      // Lap completion from backend payload
      if (message.lap_completed) {
        const comp = message.lap_completed;
        const alreadyRecorded = lapHistory.current.some(l => l.lap === comp.lap_number);
        if (!alreadyRecorded) completeLap(comp.lap_time_ms, comp.lap_number, comp);
      } else if (message.lap?.lap_completed) {
        const comp = message.lap.lap_completed;
        const alreadyRecorded = lapHistory.current.some(l => l.lap === comp.lap_number);
        if (!alreadyRecorded) completeLap(comp.lap_time_ms, comp.lap_number, comp);
      } else if (message.lap?.lap_time && message.lap?.lap_number && message.lap.lap_number >= lapNumber.current) {
        const backendLapMs  = Math.round(message.lap.lap_time * 1000);
        const backendLapNum = message.lap.lap_number;
        const alreadyRecorded = lapHistory.current.some(l => l.lap === backendLapNum);
        if (!alreadyRecorded && backendLapMs > 5000) completeLap(backendLapMs, backendLapNum);
      }

      const fuel_kg = Number(raw.fuel_kg ?? message.fuel_kg ?? Math.max(3.0, 105.0 - (lapNumber.current - 1) * 1.90));
      const tyre_compound = String(raw.tyre_compound ?? message.tyre_compound ?? PRESET.compound);
      const ers_mode = String(raw.ers_mode ?? message.ers_mode ?? 'RACE BALANCED (HARVEST/DEPLOY)');
      const engine_condition = roundDec(Number(raw.engine_condition ?? Math.max(90.0, 99.5 - (lapNumber.current - 1) * 0.18)), 1);

      // ── Lerp smoothing — blend toward new frame (α=0.35 for fast values, 0.15 for slow) ──
      const prev = smoothedFrame.current;
      const α_fast = 0.40;  // speed, rpm, throttle, brake (reactive)
      const α_slow = 0.20;  // position, temps, g-forces (smoother)

      const smoothSpeed    = prev ? lerp(prev.speed,          speed,          α_fast) : speed;
      const smoothRpm      = prev ? lerp(prev.rpm,            rpm,            α_fast) : rpm;
      const smoothThrottle = prev ? lerp(prev.throttle,       throttle,       α_fast) : throttle;
      const smoothBrake    = prev ? lerp(prev.brake_pressure, brake_pressure, α_fast) : brake_pressure;
      const smoothLongG    = prev ? lerp(prev.long_g,         long_g,         α_slow) : long_g;
      const smoothLatG     = prev ? lerp(prev.lat_g,          lat_g,          α_slow) : lat_g;
      const smoothAx       = smoothLongG * 9.81;
      const smoothAy       = prev ? lerp(prev.ay,             ay,             α_slow) : ay;
      const smoothTrkX     = prev ? lerp(prev.track_x,        Number(raw.track_x ?? gps.track_x ?? 741.6), α_slow) : Number(raw.track_x ?? gps.track_x ?? 741.6);
      const smoothTrkY     = prev ? lerp(prev.track_y,        Number(raw.track_y ?? gps.track_y ?? 473.2), α_slow) : Number(raw.track_y ?? gps.track_y ?? 473.2);
      const smoothBtFL     = prev ? lerp(prev.brake_temp_fl,  brake_temp_fl,  α_slow) : brake_temp_fl;
      const smoothBtFR     = prev ? lerp(prev.brake_temp_fr,  brake_temp_fr,  α_slow) : brake_temp_fr;
      const smoothBtRL     = prev ? lerp(prev.brake_temp_rl,  brake_temp_rl,  α_slow) : brake_temp_rl;
      const smoothBtRR     = prev ? lerp(prev.brake_temp_rr,  brake_temp_rr,  α_slow) : brake_temp_rr;

      const newPoint = {
        latitude:  Number(gps.latitude  ?? 45.618),
        longitude: Number(gps.longitude ?? 9.281),
        altitude:  Number(gps.altitude  ?? 183.0),
        satellite_count: Number(gps.satellite_count ?? 14),
        fix_status: String(gps.fix_status ?? '3D_FIX'),

        speed:          roundDec(smoothSpeed, 1),
        rpm:            Math.round(smoothRpm),
        gear,
        throttle:       roundDec(smoothThrottle, 1),
        brake_pressure: roundDec(smoothBrake, 1),

        ax: roundDec(smoothAx, 2),
        ay: roundDec(smoothAy, 2),
        az: Number(imu.az ?? 9.81),
        gx: Number(imu.gx ?? 0),
        gy: Number(imu.gy ?? 0),
        gz: Number(imu.gz ?? 0),
        resultantG,
        corneringIntensity,

        long_g:   roundDec(smoothLongG, 2),
        lat_g:    roundDec(smoothLatG, 2),

        wheel_fl: roundDec(smoothSpeed, 1),
        wheel_fr: roundDec(smoothSpeed, 1),
        wheel_rl: roundDec(throttle > 85 ? smoothSpeed + 1.2 : smoothSpeed, 1),
        wheel_rr: roundDec(throttle > 85 ? smoothSpeed + 1.2 : smoothSpeed, 1),
        wheelSlipDelta,

        coolant_temp:  Number(temp.coolant_temperature ?? 92.5),
        engine_temp:   Number(temp.engine_temperature  ?? 105.0),
        brake_temp_fl: roundDec(smoothBtFL, 1),
        brake_temp_fr: roundDec(smoothBtFR, 1),
        brake_temp_rl: roundDec(smoothBtRL, 1),
        brake_temp_rr: roundDec(smoothBtRR, 1),

        tyre_wear_fl, tyre_wear_fr, tyre_wear_rl, tyre_wear_rr,
        tyre_age_lap: Number(tyre.age_lap ?? lapNumber.current),
        engine_damage: roundDec(100.0 - engine_condition, 1),
        engine_condition,

        battery_voltage, battery_current, powerKW,
        speedTrap: maxSpeedEver.current,

        track_x:     roundDec(smoothTrkX, 2),
        track_y:     roundDec(smoothTrkY, 2),
        progress,
        corner_name: String(raw.corner_name || processed.corner_name || 'Main Straight'),
        sector:      Number(raw.sector || activeSector.current || 1),
        distance:    Number(raw.distance || 0),
        drs:         Number(can.drs ?? raw.drs ?? 0),

        fuel_kg,
        tyre_compound,
        ers_mode,

        timestamp:           Number(meta.timestamp ?? Date.now() / 1000),
        sequence_number:     Number(meta.sequence_number ?? 0),
        sampling_rate:       Number(meta.sampling_rate ?? 20),
        status_error_information: String(meta.status_error_information ?? 'OK'),
        transmission_information: isActualHardware
          ? (transmissionInfo.includes('ESP32') ? transmissionInfo : 'ESP32_SERIAL_CAN')
          : 'FastF1 Telemetry (Monza)',
      };

      smoothedFrame.current  = newPoint;
      lastValidFrame.current = newPoint;
      setData(newPoint);
      setIsConnected(true);
      setIsStale(false);

      if (staleTimer.current) clearTimeout(staleTimer.current);
      staleTimer.current = setTimeout(() => setIsStale(true), 3000);

      // Rolling history (throttle only every 2nd frame to keep chart smooth but not huge)
      setHistory(prev => {
        const next = [...prev, newPoint];
        const trimmed = next.length > 300 ? next.slice(-300) : next;
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
  }, [checkSectorTransition, completeLap]);

  // ── Fallback FastF1 playback (20 Hz with sub-frame lerp) ─────────────────────
  useEffect(() => {
    if (!FALLBACK_TELEMETRY.length) return;
    let idxFloat = 0.0;
    let simLapNumber = 1;
    const N = FALLBACK_TELEMETRY.length;
    const lapTargetSec = PRESET.baseMs / 1000;
    const intervalMs = 50; // 20 Hz
    const idxStep = N / ((lapTargetSec * 1000) / intervalMs);

    const simTimer = setInterval(() => {
      // Yield to WebSocket when it is active
      if (Date.now() - lastExternalPacketMs.current < 2000) return;

      const i1 = Math.floor(idxFloat) % N;
      const i2 = (i1 + 1) % N;
      const frac = idxFloat - Math.floor(idxFloat);
      const f1 = FALLBACK_TELEMETRY[i1];
      const f2 = FALLBACK_TELEMETRY[i2];
      if (!f1 || !f2) return;

      // Interpolate between frames
      const lerpNum = (a, b) => a + (b - a) * frac;
      const speed_adj   = roundDec(lerpNum(f1.speed, f2.speed), 1);
      const rpm_adj     = Math.round(lerpNum(f1.rpm, f2.rpm));
      const raw_thr     = roundDec(lerpNum(f1.throttle, f2.throttle), 1);
      const raw_brk     = roundDec(lerpNum(f1.brake_pressure, f2.brake_pressure), 1);
      const throttle    = raw_brk > 15 ? 0.0 : raw_thr;
      const brake       = raw_thr > 15 ? 0.0 : raw_brk;
      const track_x     = roundDec(lerpNum(f1.track_x, f2.track_x), 2);
      const track_y     = roundDec(lerpNum(f1.track_y, f2.track_y), 2);
      const lat         = roundDec(lerpNum(f1.latitude, f2.latitude), 6);
      const lon         = roundDec(lerpNum(f1.longitude, f2.longitude), 6);
      const src         = frac >= 0.5 ? f2 : f1;
      const fuel_kg     = Math.max(3.0, roundDec(105.0 - (simLapNumber - 1) * 1.90 - (src.progress * 1.90), 2));

      // Lap wrap-around lap completion
      let lapCompleted = null;
      if (i1 === 0 && idxFloat < idxStep && simLapNumber > 1) {
        const prevLap = simLapNumber - 1;
        const delta = PRESET.deltas[(prevLap - 1) % PRESET.deltas.length];
        const lapTimeMs = PRESET.baseMs + delta;
        lapCompleted = {
          lap_number: prevLap,
          lap_time_ms: lapTimeMs,
          lap_time: lapTimeMs / 1000,
          s1: Math.round(PRESET.s1Ms + (delta * 0.35)) / 1000,
          s2: Math.round(PRESET.s2Ms + (delta * 0.45)) / 1000,
          s3: Math.round(lapTimeMs - (PRESET.s1Ms + (delta * 0.35)) - (PRESET.s2Ms + (delta * 0.45))) / 1000,
        };
      }

      const alerts = [];
      if (brake > 80) {
        alerts.push({ id: 'heavy_braking_zone', severity: 'warning', alert_type: 'HEAVY BRAKING ZONE',
          message: `Threshold decel ${(src.long_g || 0).toFixed(1)}G into ${src.corner_name || 'Turn'}` });
      } else if (speed_adj > 330 && src.drs > 0) {
        alerts.push({ id: 'speed_trap_active', severity: 'info', alert_type: 'DRS HIGH SPEED TRAP',
          message: `VMAX ${speed_adj.toFixed(0)} km/h - DRS Active on Rettifilo` });
      }

      const syntheticPacket = {
        type: 'telemetry_update',
        timestamp: Date.now() / 1000,
        fuel_kg,
        tyre_compound: PRESET.compound,
        ers_mode: 'RACE BALANCED (HARVEST/DEPLOY)',
        lap_completed: lapCompleted,
        raw: {
          gps: { latitude: lat, longitude: lon, altitude: 183.0, speed: speed_adj,
            satellite_count: 14, fix_status: '3D_FIX', track_x, track_y },
          vehicle_can: { rpm: rpm_adj, gear: src.gear, throttle, brake_pressure: brake,
            battery_voltage: 14.2, battery_current: 2.5, drs: src.drs },
          imu: { ax: roundDec(lerpNum(f1.ax, f2.ax), 2), ay: roundDec(lerpNum(f1.ay, f2.ay), 2),
            az: 9.81, gx: 0.0, gy: 0.0, gz: roundDec((src.lat_g || 0) * 0.12, 3) },
          temperature: { coolant_temperature: roundDec(lerpNum(f1.coolant_temp, f2.coolant_temp), 1),
            engine_temperature: roundDec(lerpNum(f1.engine_temp, f2.engine_temp), 1),
            brake_temp_fl: roundDec(520.0 + (brake / 100) * 520, 1),
            brake_temp_fr: roundDec(518.0 + (brake / 100) * 520, 1),
            brake_temp_rl: roundDec(470.0 + (brake / 100) * 440, 1),
            brake_temp_rr: roundDec(468.0 + (brake / 100) * 440, 1) },
          wheel_speeds: { front_left: speed_adj, front_right: speed_adj,
            rear_left: roundDec(speed_adj + (throttle > 85 ? 1.2 : 0), 1),
            rear_right: roundDec(speed_adj + (throttle > 85 ? 1.2 : 0), 1) },
          tyre_wear: { fl: roundDec(8.0 + simLapNumber * 2.2, 1),
            fr: roundDec(7.0 + simLapNumber * 1.9, 1),
            rl: roundDec(6.5 + simLapNumber * 1.8, 1),
            rr: roundDec(6.0 + simLapNumber * 1.7, 1), age_lap: simLapNumber },
          metadata: { timestamp: Date.now() / 1000, sequence_number: Math.round(idxFloat),
            sampling_rate: 20, status_error_information: 'OK',
            transmission_information: 'FastF1 Telemetry (Monza GP)' },
          track_x, track_y, speed: speed_adj, rpm: rpm_adj, gear: src.gear,
          throttle, brake_pressure: brake, corner_name: src.corner_name,
          sector: src.sector, distance: roundDec(lerpNum(f1.distance_m, f2.distance_m), 1),
          progress: roundDec(lerpNum(f1.progress, f2.progress), 4),
          fuel_kg, tyre_compound: PRESET.compound, ers_mode: 'RACE BALANCED (HARVEST/DEPLOY)',
          speedTrap: 343.0,
        },
        processed: {
          longitudinal_acceleration: roundDec(lerpNum(f1.ax, f2.ax), 2),
          lateral_acceleration: roundDec(lerpNum(f1.ay, f2.ay), 2),
          vertical_acceleration: 9.81,
          long_g: roundDec(lerpNum(f1.long_g, f2.long_g), 2),
          lat_g: roundDec(lerpNum(f1.lat_g, f2.lat_g), 2),
          resultant_g: roundDec(lerpNum(f1.resultant_g, f2.resultant_g), 2),
          cornering_intensity: Math.round(lerpNum(f1.cornering_intensity, f2.cornering_intensity)),
          braking_intensity: brake,
          corner_name: src.corner_name,
        },
        alerts,
      };

      handleIngestedFrame(syntheticPacket, false);

      idxFloat += idxStep;
      if (idxFloat >= N) {
        idxFloat -= N;
        simLapNumber += 1;
      }
    }, intervalMs);

    return () => clearInterval(simTimer);
  }, [handleIngestedFrame]);

  // ── WebSocket ─────────────────────────────────────────────────────────────────
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