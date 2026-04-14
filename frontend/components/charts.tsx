"use client";

import { cloneElement, useEffect, useState, type ReactElement } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  ComposedChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { BenfordDigit, VelocitySpike } from "@/lib/contracts";

/* ------------------------------------------------------------------ */
/* Theme-aware colour helpers                                          */
/* ------------------------------------------------------------------ */

type ChartTheme = {
  inkStrong: string;
  inkMuted: string;
  inkSoft: string;
  bgTooltip: string;
  gridStroke: string;
};

const DARK_DEFAULTS: ChartTheme = {
  inkStrong: "#e8e4dc",
  inkMuted: "#636d78",
  inkSoft: "#9ba4ac",
  bgTooltip: "rgba(18, 24, 35, 0.92)",
  gridStroke: "rgba(120,140,150,0.12)",
};

function resolveTheme(): ChartTheme {
  if (typeof window === "undefined") return DARK_DEFAULTS;
  const style = getComputedStyle(document.documentElement);
  return {
    inkStrong: style.getPropertyValue("--ink-strong").trim() || DARK_DEFAULTS.inkStrong,
    inkMuted: style.getPropertyValue("--ink-muted").trim() || DARK_DEFAULTS.inkMuted,
    inkSoft: style.getPropertyValue("--ink-soft").trim() || DARK_DEFAULTS.inkSoft,
    bgTooltip: style.getPropertyValue("--bg-surface-strong").trim() || DARK_DEFAULTS.bgTooltip,
    gridStroke: "rgba(120,140,150,0.12)",
  };
}

function useChartTheme(): ChartTheme {
  const [theme, setTheme] = useState<ChartTheme>(DARK_DEFAULTS);

  useEffect(() => {
    setTheme(resolveTheme());
    const observer = new MutationObserver(() => setTheme(resolveTheme()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  return theme;
}

function tooltipStyle(t: ChartTheme): React.CSSProperties {
  return {
    background: t.bgTooltip,
    border: "none",
    borderRadius: 12,
    color: t.inkStrong,
    fontSize: "0.82rem",
  };
}

const TEST_CHART_WIDTH = 640;
const IS_JSDOM = typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent);

type ChartElementProps = {
  width?: number;
  height?: number;
};

function ResponsiveChartFrame({
  height,
  children,
}: {
  height: number;
  children: ReactElement<ChartElementProps>;
}) {
  return (
    <div className="chart-container" style={{ height }}>
      {IS_JSDOM ? (
        cloneElement(children, { width: TEST_CHART_WIDTH, height })
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      )}
    </div>
  );
}

function formatChartLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

/* ------------------------------------------------------------------ */
/* Colour helpers                                                      */
/* ------------------------------------------------------------------ */

const SEVERITY_COLORS: Record<string, string> = {
  low: "#3b9b7a",
  medium: "#5e8fa8",
  high: "#d48c28",
  critical: "#d0533a",
};

const STATUS_COLORS: Record<string, string> = {
  open: "#d48c28",
  investigating: "#5e8fa8",
  escalated: "#d0533a",
  resolved: "#3b9b7a",
  closed: "#7f8f92",
};

const RISK_COLORS: Record<string, string> = {
  low: "#3b9b7a",
  medium: "#5e8fa8",
  high: "#d48c28",
  critical: "#d0533a",
};

/* ------------------------------------------------------------------ */
/* Risk Distribution Donut                                             */
/* ------------------------------------------------------------------ */

type RiskDonutProps = {
  data: Record<string, number>;
};

export function RiskDonutChart({ data }: RiskDonutProps) {
  const t = useChartTheme();
  const entries = Object.entries(data).map(([name, value]) => ({
    name: formatChartLabel(name),
    value,
    fill: RISK_COLORS[name] ?? "#7f8f92",
  }));

  if (entries.length === 0) return null;

  return (
    <ResponsiveChartFrame height={220}>
      <PieChart>
        <Pie
          data={entries}
          cx="50%"
          cy="50%"
          innerRadius={55}
          outerRadius={85}
          paddingAngle={3}
          dataKey="value"
          stroke="none"
          animationDuration={800}
        >
          {entries.map((entry) => (
            <Cell key={entry.name} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle(t)} />
        <Legend
          verticalAlign="bottom"
          iconType="circle"
          iconSize={8}
          formatter={(value: string | number) => (
            <span style={{ color: t.inkSoft, fontSize: "0.78rem", textTransform: "capitalize" }}>
              {value}
            </span>
          )}
        />
      </PieChart>
    </ResponsiveChartFrame>
  );
}

/* ------------------------------------------------------------------ */
/* Cases by Status Bar Chart                                           */
/* ------------------------------------------------------------------ */

type StatusBarChartProps = {
  data: Record<string, number>;
  colorMap?: Record<string, string>;
  label?: string;
};

export function StatusBarChart({ data, colorMap = STATUS_COLORS }: StatusBarChartProps) {
  const t = useChartTheme();
  const entries = Object.entries(data).map(([name, value]) => ({
    label: formatChartLabel(name),
    value,
    fill: colorMap[name] ?? "#7f8f92",
  }));

  if (entries.length === 0) return null;

  return (
    <ResponsiveChartFrame height={200}>
      <BarChart data={entries} layout="vertical" margin={{ left: 10, right: 16, top: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={t.gridStroke} horizontal={false} />
        <XAxis type="number" tick={{ fontSize: 11, fill: t.inkMuted }} axisLine={false} tickLine={false} />
        <YAxis
          dataKey="label"
          type="category"
          tick={{ fontSize: 11, fill: t.inkSoft }}
          axisLine={false}
          tickLine={false}
          width={90}
        />
        <Tooltip contentStyle={tooltipStyle(t)} />
        <Bar dataKey="value" radius={[0, 6, 6, 0]} animationDuration={600}>
          {entries.map((entry) => (
            <Cell key={entry.label} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveChartFrame>
  );
}

/* ------------------------------------------------------------------ */
/* Alerts by Severity Bar Chart                                        */
/* ------------------------------------------------------------------ */

export function SeverityBarChart({ data }: { data: Record<string, number> }) {
  return <StatusBarChart data={data} colorMap={SEVERITY_COLORS} />;
}

/* ------------------------------------------------------------------ */
/* Benford's Law Comparison Chart                                      */
/* ------------------------------------------------------------------ */

type BenfordChartProps = {
  digits: BenfordDigit[];
};

export function BenfordChart({ digits }: BenfordChartProps) {
  const t = useChartTheme();
  const chartData = digits.map((d) => ({
    digit: String(d.digit),
    Expected: parseFloat(d.expected_pct.toFixed(1)),
    Actual: parseFloat(d.actual_pct.toFixed(1)),
    deviation: d.deviation,
  }));

  return (
    <ResponsiveChartFrame height={240}>
      <ComposedChart data={chartData} margin={{ left: -10, right: 12, top: 8, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={t.gridStroke} />
        <XAxis dataKey="digit" tick={{ fontSize: 12, fill: t.inkSoft }} axisLine={false} tickLine={false} />
        <YAxis
          tick={{ fontSize: 11, fill: t.inkMuted }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip
          contentStyle={tooltipStyle(t)}
          formatter={(value) => `${String(value)}%`}
        />
        <Legend
          iconType="circle"
          iconSize={8}
          formatter={(value: string | number) => (
            <span style={{ color: t.inkSoft, fontSize: "0.78rem" }}>{value}</span>
          )}
        />
        <Bar dataKey="Expected" fill="#5e8fa8" opacity={0.45} radius={[4, 4, 0, 0]} barSize={20} animationDuration={600} />
        <Bar dataKey="Actual" fill="#d0533a" radius={[4, 4, 0, 0]} barSize={20} animationDuration={600} />
        <Line
          type="monotone"
          dataKey="Expected"
          stroke="#5e8fa8"
          strokeWidth={2}
          strokeDasharray="5 5"
          dot={false}
        />
      </ComposedChart>
    </ResponsiveChartFrame>
  );
}

/* ------------------------------------------------------------------ */
/* Velocity Spike Timeline                                             */
/* ------------------------------------------------------------------ */

type VelocityChartProps = {
  spikes: VelocitySpike[];
};

export function VelocityChart({ spikes }: VelocityChartProps) {
  const t = useChartTheme();
  if (spikes.length === 0) return null;

  const data = spikes.map((s, i) => ({
    name: `${s.entity_type.slice(0, 4)}-${s.entity_id.slice(0, 6)}`,
    index: i,
    zScore: parseFloat(s.z_score.toFixed(1)),
    transactions: s.transaction_count,
    amount: s.total_amount,
  }));

  return (
    <ResponsiveChartFrame height={200}>
      <BarChart data={data} margin={{ left: -10, right: 12, top: 8, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={t.gridStroke} />
        <XAxis dataKey="name" tick={{ fontSize: 10, fill: t.inkMuted }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: t.inkMuted }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={tooltipStyle(t)}
          formatter={(value, name) => {
            const seriesName = String(name ?? "");
            if (seriesName === "zScore") return [`${String(value)}σ`, "Z-Score"];
            return [String(value), formatChartLabel(seriesName)];
          }}
        />
        <Bar dataKey="zScore" name="Z-Score" radius={[6, 6, 0, 0]} animationDuration={600}>
          {data.map((entry) => (
            <Cell
              key={entry.name}
              fill={entry.zScore > 3 ? "#d0533a" : entry.zScore > 2 ? "#d48c28" : "#5e8fa8"}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveChartFrame>
  );
}

/* ------------------------------------------------------------------ */
/* Animated Risk Gauge                                                 */
/* ------------------------------------------------------------------ */

type RiskGaugeProps = {
  score: number;
  level: string;
  label?: string;
};

export function RiskGauge({ score, level, label = "Risk Score" }: RiskGaugeProps) {
  const t = useChartTheme();
  const clampedScore = Math.min(100, Math.max(0, score));
  const sweepAngle = (clampedScore / 100) * 180;
  const color = RISK_COLORS[level] ?? "#7f8f92";

  // SVG arc path
  const polarToCartesian = (cx: number, cy: number, r: number, angleDeg: number) => {
    const rad = ((angleDeg - 180) * Math.PI) / 180;
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
  };

  const r = 70;
  const cx = 90;
  const cy = 85;
  const start = polarToCartesian(cx, cy, r, 0);
  const end = polarToCartesian(cx, cy, r, sweepAngle);
  const largeArc = sweepAngle > 180 ? 1 : 0;
  const arcPath = `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 1 ${end.x} ${end.y}`;

  // Background arc (full half-circle)
  const bgEnd = polarToCartesian(cx, cy, r, 180);
  const bgPath = `M ${start.x} ${start.y} A ${r} ${r} 0 0 1 ${bgEnd.x} ${bgEnd.y}`;

  return (
    <div className="risk-gauge">
      <svg width="180" height="110" viewBox="0 0 180 110">
        <path d={bgPath} fill="none" stroke="rgba(120,140,150,0.15)" strokeWidth="14" strokeLinecap="round" />
        <path
          d={arcPath}
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          style={{ transition: "all 0.8s ease" }}
        />
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize="28" fontWeight="700" fill={color}>
          {score}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fontSize="10" fill={t.inkMuted} letterSpacing="0.08em">
          {label.toUpperCase()}
        </text>
      </svg>
      <span className={`risk-chip ${level}`} style={{ marginTop: 4 }}>{level}</span>
    </div>
  );
}
