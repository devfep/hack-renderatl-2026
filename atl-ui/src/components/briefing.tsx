"use client";

/**
 * The standing briefing: what the harvest found, shown before anyone asks anything.
 *
 * Colours are the validated dark-mode tokens - ink at #ffffff / #c3c2b7 / #898781 on the
 * #1a1a19 surface, and one accent hue (#3987e5) that clears 3:1 against it. A single series
 * needs no legend, so every bar is directly labelled instead.
 */

import { Sources } from "@/components/sources";

const INK = "#ffffff";
const INK_SECONDARY = "#c3c2b7";
const INK_MUTED = "#898781";
const SURFACE = "#1a1a19";
const GRIDLINE = "#2c2c2a";
const ACCENT = "#3987e5";

const COMPARISON = [
  { label: "Inside a Community of Concern", stops: "464 stops", trips: 41 },
  { label: "Everywhere else", stops: "6,549 stops", trips: 40 },
];

/** Sorted ascending so the two lagging areas read as the tail, not as outliers. */
const AREAS = [
  { name: "Bankhead Courts / Bolton", noVehicle: "34.4%", trips: 20 },
  { name: "Ivan Hill", noVehicle: "31.0%", trips: 30 },
  { name: "Vine City", noVehicle: "49.2%", trips: 62 },
  { name: "Campbellton Road", noVehicle: "31.7%", trips: 80 },
];

const MAX_TRIPS = 80;

export function Briefing() {
  return (
    <div
      style={{ background: SURFACE, color: INK }}
      className="mx-auto max-w-3xl rounded-lg px-8 py-10"
    >
      <h1 className="text-3xl font-semibold tracking-tight" style={{ color: INK }}>
        Atlanta Transit Agent
      </h1>
      <p className="mt-3 text-lg" style={{ color: INK_SECONDARY }}>
        I set out to prove MARTA underserves Atlanta&rsquo;s poorest neighbourhoods. The data
        refused.
      </p>

      <section className="mt-10">
        <h2
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: INK_MUTED }}
        >
          Median weekday trips per stop
        </h2>
        <div className="mt-4 space-y-3">
          {COMPARISON.map((row) => (
            <div key={row.label} className="flex items-baseline gap-4 text-sm">
              <span className="w-60 shrink-0" style={{ color: INK_SECONDARY }}>
                {row.label}
              </span>
              <span className="w-24 shrink-0 tabular-nums" style={{ color: INK_MUTED }}>
                {row.stops}
              </span>
              <span className="text-2xl font-semibold tabular-nums" style={{ color: INK }}>
                {row.trips}
              </span>
            </div>
          ))}
        </div>
        <p className="mt-4 text-sm" style={{ color: INK_SECONDARY }}>
          Service is marginally <em>higher</em> where the city says need is greatest. The
          correlation between car-free households and bus service is +0.27 &mdash; positive.
        </p>
      </section>

      <section className="mt-10">
        <h2
          className="text-xs font-semibold uppercase tracking-wider"
          style={{ color: INK_MUTED }}
        >
          But two places lag, at comparable need
        </h2>
        <div className="mt-4 space-y-3">
          {AREAS.map((area) => (
            <div key={area.name} className="flex items-center gap-4 text-sm">
              <span className="w-52 shrink-0 truncate" style={{ color: INK_SECONDARY }}>
                {area.name}
              </span>
              <span className="w-20 shrink-0 tabular-nums" style={{ color: INK_MUTED }}>
                {area.noVehicle} no car
              </span>
              <div className="flex flex-1 items-center gap-2">
                <div
                  className="h-2.5 rounded-r"
                  style={{
                    width: `${(area.trips / MAX_TRIPS) * 100}%`,
                    background: ACCENT,
                    borderRadius: "0 4px 4px 0",
                  }}
                  aria-hidden
                />
                <span className="tabular-nums font-medium" style={{ color: INK }}>
                  {area.trips}
                </span>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-4 border-t pt-4 text-sm" style={{ color: INK_SECONDARY, borderColor: GRIDLINE }}>
          A 4&times; spread inside the city&rsquo;s own high-need areas. Ask the agent about any
          of them &mdash; it queries MARTA&rsquo;s schedule and the Communities of Concern layer
          directly, and every figure it gives you comes back from that query.
        </p>
      </section>

      <Sources />
    </div>
  );
}
