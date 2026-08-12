"use client";

/**
 * The main panel, driven by whatever the agent last returned.
 *
 * Nothing here is hardcoded per question. `ask_transit` hands back the columns and rows the
 * Cortex-written SQL actually produced, and this picks a form from that shape: a bar chart
 * when there is one label and one number, a table otherwise. Until something is asked it
 * shows the standing briefing.
 */

import { useAgent } from "@copilotkit/react-core/v2";

import { Briefing } from "@/components/briefing";

const INK = "#ffffff";
const INK_SECONDARY = "#c3c2b7";
const INK_MUTED = "#898781";
const SURFACE = "#1a1a19";
const GRIDLINE = "#2c2c2a";
const ACCENT = "#3987e5";

type Row = (string | number | null)[];

interface Result {
  summary?: string;
  sql?: string;
  columns?: string[];
  rows?: Row[];
  row_count?: number;
}

/** Pull the most recent ask_transit payload out of the conversation, if there is one. */
function latestResult(messages: unknown[]): Result | null {
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i] as { role?: string; content?: unknown };
    if (message?.role !== "tool" || typeof message.content !== "string") continue;
    try {
      const parsed = JSON.parse(message.content) as Result;
      if (Array.isArray(parsed?.columns) && Array.isArray(parsed?.rows)) return parsed;
    } catch {
      // Not every tool result is JSON; keep looking back through the thread.
    }
  }
  return null;
}

/** A chart only earns its place when one column labels and exactly one measures. */
function chartable(result: Result): { labels: string[]; values: number[] } | null {
  const { columns = [], rows = [] } = result;
  if (columns.length !== 2 || rows.length < 2 || rows.length > 15) return null;
  const numericIndex = [0, 1].find((i) => rows.every((r) => typeof r[i] === "number"));
  if (numericIndex === undefined) return null;
  const labelIndex = numericIndex === 0 ? 1 : 0;
  if (!rows.every((r) => typeof r[labelIndex] === "string")) return null;
  return {
    labels: rows.map((r) => String(r[labelIndex])),
    values: rows.map((r) => Number(r[numericIndex])),
  };
}

export function ResultPanel({ agentId }: { agentId: string }) {
  const { agent } = useAgent({ agentId });
  const messages = ((agent as { messages?: unknown[] })?.messages ?? []) as unknown[];
  const result = latestResult(messages);

  if (!result) return <Briefing />;

  const chart = chartable(result);
  return (
    <div
      style={{ background: SURFACE, color: INK }}
      className="mx-auto max-w-3xl rounded-lg px-8 py-10"
    >
      <h2 className="text-xs font-semibold uppercase tracking-wider" style={{ color: INK_MUTED }}>
        What the agent just queried
      </h2>

      {result.summary ? (
        <p className="mt-3 text-lg leading-snug" style={{ color: INK }}>
          {result.summary}
        </p>
      ) : null}

      {chart ? <Bars labels={chart.labels} values={chart.values} /> : <Table result={result} />}

      {result.sql ? (
        <details className="mt-8">
          <summary className="cursor-pointer text-xs uppercase tracking-wider" style={{ color: INK_MUTED }}>
            The SQL Cortex wrote
          </summary>
          <pre
            className="mt-3 overflow-x-auto rounded p-3 text-xs leading-relaxed"
            style={{ background: "#0d0d0d", color: INK_SECONDARY }}
          >
            {result.sql}
          </pre>
        </details>
      ) : null}

      {typeof result.row_count === "number" ? (
        <p className="mt-4 text-xs" style={{ color: INK_MUTED }}>
          {result.row_count} row{result.row_count === 1 ? "" : "s"} returned
          {result.rows && result.row_count > result.rows.length
            ? `, showing ${result.rows.length}`
            : ""}
        </p>
      ) : null}
    </div>
  );
}

function Bars({ labels, values }: { labels: string[]; values: number[] }) {
  const max = Math.max(...values, 1);
  return (
    <div className="mt-6 space-y-3">
      {labels.map((label, i) => (
        <div key={`${label}-${i}`} className="flex items-center gap-4 text-sm">
          <span className="w-56 shrink-0 truncate" style={{ color: INK_SECONDARY }} title={label}>
            {label}
          </span>
          <div className="flex flex-1 items-center gap-2">
            <div
              className="h-2.5"
              style={{
                width: `${(values[i] / max) * 100}%`,
                background: ACCENT,
                borderRadius: "0 4px 4px 0",
              }}
              aria-hidden
            />
            <span className="tabular-nums font-medium" style={{ color: INK }}>
              {values[i].toLocaleString()}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}

function Table({ result }: { result: Result }) {
  const { columns = [], rows = [] } = result;
  return (
    <div className="mt-6 overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c}
                className="border-b py-2 pr-6 text-left text-xs font-semibold uppercase tracking-wider"
                style={{ color: INK_MUTED, borderColor: GRIDLINE }}
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 15).map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td
                  key={j}
                  className="border-b py-2 pr-6 tabular-nums"
                  style={{ color: typeof cell === "number" ? INK : INK_SECONDARY, borderColor: GRIDLINE }}
                >
                  {cell === null ? "—" : String(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
