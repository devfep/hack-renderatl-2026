"use client";

import {
  CopilotChatConfigurationProvider,
  CopilotSidebar,
  CopilotThreadsDrawer,
  useConfigureSuggestions,
} from "@copilotkit/react-core/v2";
import React from "react";

import styles from "./page.module.css";

// The agent key registered in the runtime route (`agents: { default: ... }`).
const AGENT_ID = "default";

/** Figures from the harvest, shown so a first-time visitor has context to ask about. */
const FINDING = [
  { label: "Inside a Community of Concern", stops: "464", trips: "41" },
  { label: "Everywhere else", stops: "6,549", trips: "40" },
];

const GAPS = [
  { name: "Campbellton Road", noVehicle: "31.7%", trips: 80 },
  { name: "Vine City", noVehicle: "49.2%", trips: 62 },
  { name: "Ivan Hill", noVehicle: "31.0%", trips: 30 },
  { name: "Bankhead Courts / Bolton", noVehicle: "34.4%", trips: 20 },
];

export default function AtlTransitPage() {
  useConfigureSuggestions({
    suggestions: [
      {
        title: "Least served",
        message:
          "Which Atlanta Communities of Concern get the least weekday bus service?",
      },
      {
        title: "Test the premise",
        message:
          "Prove that MARTA discriminates against poor Atlanta neighbourhoods.",
      },
      {
        title: "Right now",
        message: "Where are MARTA buses right now?",
      },
      {
        title: "The network",
        message: "How many bus routes does MARTA operate?",
      },
    ],
  });

  return (
    <CopilotChatConfigurationProvider agentId={AGENT_ID}>
      <div className={`${styles.layout} threadsLayout`}>
        <CopilotThreadsDrawer agentId={AGENT_ID} />
        <div className={styles.mainPanel}>
          <main>
            <Briefing />
            <CopilotSidebar
              defaultOpen={true}
              labels={{
                modalHeaderTitle: "Atlanta Transit Agent",
                welcomeMessageText:
                  "Ask me anything about MARTA service and Atlanta's Communities of Concern. Every number I give you comes from the data, not from memory.",
              }}
            />
          </main>
        </div>
      </div>
    </CopilotChatConfigurationProvider>
  );
}

function Briefing() {
  return (
    <div className="mx-auto max-w-3xl px-8 py-12 text-slate-800">
      <h1 className="text-3xl font-semibold tracking-tight">
        Atlanta Transit Agent
      </h1>
      <p className="mt-3 text-lg text-slate-600">
        We set out to prove MARTA underserves Atlanta&rsquo;s poorest
        neighbourhoods. The data refused.
      </p>

      <section className="mt-10">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Median weekday trips per stop
        </h2>
        <table className="mt-3 w-full border-collapse text-sm">
          <tbody>
            {FINDING.map((row) => (
              <tr key={row.label} className="border-b border-slate-200">
                <td className="py-2">{row.label}</td>
                <td className="py-2 text-right tabular-nums text-slate-500">
                  {row.stops} stops
                </td>
                <td className="py-2 pl-6 text-right text-lg font-semibold tabular-nums">
                  {row.trips}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-sm text-slate-600">
          Service is marginally <em>higher</em> where the city says need is
          greatest. The correlation between car-free households and bus service
          is +0.27 — positive.
        </p>
      </section>

      <section className="mt-10">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          But two places lag, at comparable need
        </h2>
        <ul className="mt-3 space-y-2">
          {GAPS.map((gap) => (
            <li key={gap.name} className="flex items-center gap-3 text-sm">
              <span className="w-56 shrink-0">{gap.name}</span>
              <span className="w-20 shrink-0 tabular-nums text-slate-500">
                {gap.noVehicle} no car
              </span>
              <span
                className="h-3 rounded-sm bg-slate-800"
                style={{ width: `${gap.trips * 3}px` }}
                aria-hidden
              />
              <span className="tabular-nums font-medium">{gap.trips}</span>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-sm text-slate-600">
          A 4&times; spread inside the city&rsquo;s own high-need areas. Ask the
          agent about any of them &mdash; it queries MARTA&rsquo;s schedule and
          the Communities of Concern layer directly.
        </p>
      </section>
    </div>
  );
}
