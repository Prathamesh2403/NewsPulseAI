import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { SENTIMENT_TREND, CATEGORY_SHARE, STATS } from '../../data/mockArticles'

/* ── Shared card wrapper ─────────────────────────────────────────── */
function SideCard({ title, children, className = '' }) {
  return (
    <div
      className={`bg-white p-5 ${className}`}
      style={{
        borderRadius: 'var(--radius)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      {title && (
        <p style={{
          fontSize: 13,
          fontWeight: 600,
          color: 'var(--color-gray-700)',
          marginBottom: 12,
        }}>
          {title}
        </p>
      )}
      {children}
    </div>
  )
}

/* ── Stat mini-card ──────────────────────────────────────────────── */
function StatCard({ label, value, sub, subColor }) {
  return (
    <div
      className="flex-1 flex flex-col gap-1"
      style={{
        borderRadius: 'var(--radius-sm)',
        padding: '14px 12px',
        background: 'var(--color-gray-50)',
      }}
    >
      <p style={{ fontSize: 11, fontWeight: 500, color: 'var(--color-gray-400)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {label}
      </p>
      <p style={{ fontSize: 26, fontWeight: 700, lineHeight: 1, color: 'var(--color-gray-900)' }}>
        {value}
      </p>
      <p style={{ fontSize: 12, fontWeight: 600, color: subColor ?? 'var(--color-teal)' }}>
        {sub}
      </p>
    </div>
  )
}

/* ── Custom tooltip for sentiment chart ─────────────────────────── */
function SentimentTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--color-gray-900)',
      color: '#fff',
      borderRadius: 8,
      padding: '8px 12px',
      fontSize: 11,
      boxShadow: 'var(--shadow-lg)',
    }}>
      <p style={{ fontWeight: 600, marginBottom: 4 }}>{label}</p>
      {payload.map(p => (
        <div key={p.dataKey} className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span style={{ textTransform: 'capitalize' }}>{p.dataKey}:</span>
          <span style={{ fontWeight: 600 }}>{p.value}%</span>
        </div>
      ))}
    </div>
  )
}

/* ── Custom legend for donut chart ──────────────────────────────── */
function DonutLegend() {
  return (
    <div className="flex flex-col gap-2 mt-4">
      {CATEGORY_SHARE.map(item => (
        <div key={item.name} className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: item.color }}
            />
            <span style={{ fontSize: 12, color: 'var(--color-gray-600)' }}>
              {item.name}
            </span>
          </div>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-gray-800)' }}>
            {item.value}%
          </span>
        </div>
      ))}
    </div>
  )
}

/* ── PulseSidebar ────────────────────────────────────────────────── */
export default function PulseSidebar() {
  return (
    <aside className="flex flex-col gap-4">
      {/* Heading */}
      <div className="flex items-center gap-2.5">
        <h2 style={{ fontSize: 16, fontWeight: 700, color: 'var(--color-gray-900)' }}>
          Pulse
        </h2>
        {/* Live indicator */}
        <span
          className="flex items-center gap-1.5"
          style={{
            padding: '3px 8px',
            borderRadius: 20,
            fontSize: 10,
            fontWeight: 600,
            background: 'rgba(62,207,180,0.12)',
            color: '#0F8A6F',
          }}
        >
          <span
            className="w-[6px] h-[6px] rounded-full animate-pulse"
            style={{ backgroundColor: 'var(--color-teal)' }}
          />
          Live
        </span>
      </div>

      {/* Stat cards row */}
      <div className="flex gap-3">
        <StatCard
          label="Articles Today"
          value={STATS.articlesToday}
          sub={STATS.articlesTodayChange}
          subColor="var(--color-teal)"
        />
        <StatCard
          label="Top Category"
          value={STATS.topCategory}
          sub={STATS.topCategoryPct}
          subColor="var(--color-primary)"
        />
      </div>

      {/* Sentiment trend chart */}
      <SideCard title="Sentiment, last 7 days">
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={SENTIMENT_TREND} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
            <defs>
              <linearGradient id="gradPos" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3ECFB4" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#3ECFB4" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradNeg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#F06D6D" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#F06D6D" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradNeu" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#A1A1AA" stopOpacity={0.15} />
                <stop offset="95%" stopColor="#A1A1AA" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="day"
              tick={{ fontSize: 10, fill: '#A1A1AA' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis hide />
            <Tooltip content={<SentimentTooltip />} />
            <Area type="monotone" dataKey="positive" stroke="#3ECFB4" strokeWidth={2}
                  fill="url(#gradPos)" dot={false} activeDot={{ r: 3, strokeWidth: 0 }} />
            <Area type="monotone" dataKey="neutral" stroke="#A1A1AA" strokeWidth={1.5}
                  fill="url(#gradNeu)" dot={false} activeDot={{ r: 3, strokeWidth: 0 }} />
            <Area type="monotone" dataKey="negative" stroke="#F06D6D" strokeWidth={2}
                  fill="url(#gradNeg)" dot={false} activeDot={{ r: 3, strokeWidth: 0 }} />
          </AreaChart>
        </ResponsiveContainer>
        {/* Legend */}
        <div className="flex items-center justify-center gap-5 mt-3">
          {[
            { label: 'Positive', color: '#3ECFB4' },
            { label: 'Neutral', color: '#A1A1AA' },
            { label: 'Negative', color: '#F06D6D' },
          ].map(({ label, color }) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
              <span style={{ fontSize: 11, color: 'var(--color-gray-500)' }}>{label}</span>
            </div>
          ))}
        </div>
      </SideCard>

      {/* Category share donut */}
      <SideCard title="Category share">
        <ResponsiveContainer width="100%" height={160}>
          <PieChart>
            <Pie
              data={CATEGORY_SHARE}
              cx="50%"
              cy="50%"
              innerRadius={44}
              outerRadius={66}
              paddingAngle={3}
              dataKey="value"
              strokeWidth={0}
            >
              {CATEGORY_SHARE.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, name) => [`${value}%`, name]}
              contentStyle={{
                background: 'var(--color-gray-900)',
                border: 'none',
                borderRadius: 8,
                color: '#fff',
                fontSize: 11,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <DonutLegend />
      </SideCard>
    </aside>
  )
}
