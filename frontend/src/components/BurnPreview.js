import React, { useMemo } from 'react';
import TrackListRich from './TrackListRich';

const Flag = ({ ok, label }) => (
  <span
    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold mr-2 mb-2 ${
      ok ? 'bg-brandSuccess-700 text-white' : 'bg-brandError-700 text-white'
    }`}
    title={label}
  >
    {ok ? '✔' : '✖'}
    <span className="ml-1">{label}</span>
  </span>
);

const fmtTime = (secs) => {
  if (!secs && secs !== 0) return '--:--';
  const s = Math.round(secs);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, '0')}`;
};

const BurnPreview = ({ plan, onStart, initiating = false, inProgress = false, canStart = false, disabledReason }) => {
  const total = Math.max(0, Number(plan?.total_duration_sec || 0));

  const summary = useMemo(() => ({
    title: plan?.disc_title || 'Audio CD',
    artist: plan?.album_artist || '',
    count: plan?.track_count || 0,
    totalFmt: fmtTime(total),
    warnings: plan?.warnings || [],
  }), [plan, total]);

  const flags = useMemo(() => {
    const missing = (plan?.missing_tracks || []).length === 0;
    const primaryMin = Number(plan?.capacity_primary_min || 80);
    const primaryFit = plan?.fits_primary ?? (total <= primaryMin * 60);
    return {
      statusOk: plan?.status === 'ok',
      primaryMin,
      fitsPrimary: Boolean(primaryFit),
      noMissing: missing,
    };
  }, [plan, total]);

  const previewOk = flags.statusOk && flags.fitsPrimary && flags.noMissing;

  const capacity = useMemo(() => {
    const primaryMin = Number(plan?.capacity_primary_min || 80);
    const capP = Math.max(1, primaryMin) * 60;
    const left = (cap) => cap - total;
    const label = (l) => (l >= 0 ? `${fmtTime(l)} left` : `Over by ${fmtTime(-l)}`);
    const color = (l) => (l < 0 ? 'red' : l < 120 ? 'yellow' : 'green');
    const usedPct = (cap) => Math.min(100, Math.max(0, (total / cap) * 100));
    const barClass = (l) => {
      const c = color(l);
      return c === 'red' ? 'bg-brandError-500' : c === 'yellow' ? 'bg-brandWarning-400' : 'bg-brandSuccess-500';
    };
    const textClass = (l) => {
      const c = color(l);
      return c === 'red' ? 'text-brandError-400' : c === 'yellow' ? 'text-brandWarning-300' : 'text-brandSuccess-400';
    };
    const lP = left(capP);
    return {
      primaryMin,
      labelPrimary: label(lP),
      textPrimary: textClass(lP),
      usedPrimary: usedPct(capP),
      barPrimary: barClass(lP),
    };
  }, [plan, total]);

  const enrichedTracks = useMemo(() => {
    const raw = plan?.raw_tracks || [];
    const planList = plan?.tracks || [];
    const sorted = [...raw].sort((a, b) => {
      const ad = Number(a.disc_number || 1);
      const bd = Number(b.disc_number || 1);
      if (ad !== bd) return ad - bd;
      const at = Number(a.track_number || 0);
      const bt = Number(b.track_number || 0);
      return at - bt;
    });
    return sorted.map((t, i) => ({
      ...t,
      _missing: !(planList[i] && planList[i].file),
      has_embedded_lyrics: planList[i] && typeof planList[i].has_embedded_lyrics !== 'undefined' ? planList[i].has_embedded_lyrics : undefined,
    }));
  }, [plan]);

  return (
    <section className="w-full bg-brand-50 dark:bg-gray-800 rounded-lg shadow-md p-6 mt-6 ring-1 ring-brand-100 dark:ring-0">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Burn Preview</h3>
          <p className="text-sm text-slate-700 dark:text-gray-300">
            {summary.title}
            {summary.artist ? ` — ${summary.artist}` : ''} • {summary.count} tracks • {summary.totalFmt}
          </p>
        </div>
      </div>

      <div className="mb-4">
        <Flag ok={flags.statusOk} label="Metadata OK" />
        <Flag ok={flags.noMissing} label="All files found" />
        <Flag ok={flags.fitsPrimary} label={`≤ ${flags.primaryMin} min`} />
      </div>

      <div className="mb-3 text-sm">
        <div className="flex items-center justify-between mb-1">
          <span className="text-slate-700 dark:text-gray-300">{capacity.primaryMin}-min CD</span>
          <span className={capacity.textPrimary}>{capacity.labelPrimary}</span>
        </div>
        <div className="h-2 rounded bg-brand-200 dark:bg-gray-700 overflow-hidden">
          <div className={`h-2 ${capacity.barPrimary}`} style={{ width: `${capacity.usedPrimary}%` }} />
        </div>
      </div>

      {plan?.warnings?.length > 0 && (
        <div className="mb-4 text-brandWarning-700 dark:text-brandWarning-300 text-sm">
          {plan.warnings.map((w, i) => (
            <div key={i}>⚠ {w}</div>
          ))}
        </div>
      )}

      {(plan?.missing_tracks?.length || 0) > 0 && (
        <div className="mb-4 text-brandError-600 dark:text-brandError-300 text-sm">
          <div className="font-semibold mb-1">Missing Tracks:</div>
          {plan.missing_tracks.map((m) => (
            <div key={m.index}>
              #{m.index} {m.title} — {m.artist} (expected: {m.expected.join(' or ')})
            </div>
          ))}
        </div>
      )}

      <TrackListRich tracks={enrichedTracks} compactForBurnPreview />

      <div className="mt-6 flex flex-col items-center justify-center gap-2">
        {inProgress ? (
          <div className="text-slate-700 dark:text-gray-300 text-sm">Burn in progress…</div>
        ) : (
          <>
            <button
              type="button"
              onClick={onStart}
              disabled={!(previewOk && canStart) || initiating}
              className={`py-3 px-8 rounded-lg text-lg font-bold transition duration-200 ${
                !(previewOk && canStart) || initiating
                  ? 'bg-slate-200 text-slate-400 dark:bg-gray-600 dark:text-gray-400 cursor-not-allowed'
                  : 'bg-brandSuccess-600 hover:bg-brandSuccess-700 text-white'
              }`}
            >
              {initiating ? 'Initiating Burn…' : 'Start CD Burn'}
            </button>
            {disabledReason && (!(previewOk && canStart) || initiating) && (
              <div className="text-slate-700 dark:text-gray-400 text-sm">{disabledReason}</div>
            )}
          </>
        )}
      </div>
    </section>
  );
};

export default BurnPreview;

