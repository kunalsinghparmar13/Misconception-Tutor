import React, { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { MisconceptionBugRate } from '../types/education';

interface ProgressChartProps {
  bugRates: MisconceptionBugRate[];
}

export const ProgressChart: React.FC<ProgressChartProps> = ({ bugRates }) => {
  const [hoveredPoint, setHoveredPoint] = useState<{
    misconception: string;
    session: string;
    rate: number;
    x: number;
    y: number;
  } | null>(null);

  if (!bugRates || bugRates.length === 0) {
    return (
      <div className="w-full h-64 flex flex-col items-center justify-center bg-[#1D221E] rounded-2xl border border-[#353C36] p-6 text-center backdrop-blur-md">
        <p className="text-sm font-medium text-[#F1F0E9]">No Session Data Available Yet</p>
        <p className="text-xs text-[#858D83] mt-1">Complete your first practice session to generate misconception trendlines.</p>
      </div>
    );
  }

  // Refined palette in Sage, Mint, Amber, Slate
  const colorPalette = ['#A3B5A0', '#8FBF9B', '#D8BC86', '#9EB8CC'];

  // Dimensions for responsive SVG coordinate space
  const svgWidth = 600;
  const svgHeight = 260;
  const padding = { top: 30, right: 30, bottom: 40, left: 50 };

  const chartW = svgWidth - padding.left - padding.right;
  const chartH = svgHeight - padding.top - padding.bottom;

  // Assume sessions 1, 2, 3
  const sessions = ['Session 1', 'Session 2', 'Session 3'];

  const getX = (idx: number) => {
    return padding.left + (idx / (sessions.length - 1)) * chartW;
  };

  const getY = (bugRate: number) => {
    // 0% at bottom, 100% at top
    return padding.top + chartH - (bugRate / 100) * chartH;
  };

  return (
    <div className="bg-[#222823] rounded-3xl border border-[#353C36] p-5 md:p-7 shadow-xl relative backdrop-blur-xl text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h3 className="text-base font-bold text-[#F1F0E9] tracking-tight">
            Misconception Frequency Across Learning Sessions
          </h3>
          <p className="text-xs text-[#858D83]">
            Percentage of evaluated problems triggered by each specific cognitive divergence
          </p>
        </div>
      </div>

      {/* SVG Chart Container */}
      <div className="relative w-full overflow-x-auto">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto min-w-[480px] max-h-[300px]"
        >
          {/* Grid lines and Y-axis labels */}
          {[0, 25, 50, 75, 100].map((tick) => {
            const y = getY(tick);
            return (
              <g key={`y-axis-${tick}`}>
                <line
                  x1={padding.left}
                  y1={y}
                  x2={svgWidth - padding.right}
                  y2={y}
                  stroke="rgba(53, 60, 54, 0.8)"
                  strokeDasharray={tick === 0 ? undefined : '4 4'}
                  strokeWidth={1}
                />
                <text
                  x={padding.left - 10}
                  y={y + 4}
                  textAnchor="end"
                  fill="#858D83"
                  fontSize="11"
                  fontFamily="monospace"
                >
                  {tick}%
                </text>
              </g>
            );
          })}

          {/* X-axis labels */}
          {sessions.map((sess, idx) => {
            const x = getX(idx);
            return (
              <g key={`x-axis-${sess}`}>
                <line
                  x1={x}
                  y1={svgHeight - padding.bottom}
                  x2={x}
                  y2={svgHeight - padding.bottom + 6}
                  stroke="rgba(53, 60, 54, 0.9)"
                  strokeWidth={1}
                />
                <text
                  x={x}
                  y={svgHeight - padding.bottom + 22}
                  textAnchor="middle"
                  fill="#858D83"
                  fontSize="11"
                  fontWeight="500"
                >
                  {sess}
                </text>
              </g>
            );
          })}

          {/* Trend lines for each misconception with pathLength animated drawing */}
          {bugRates.map((item, mIdx) => {
            const color = colorPalette[mIdx % colorPalette.length];
            const points = item.historicalRates.map((h, sIdx) => ({
              x: getX(sIdx),
              y: getY(h.bugRate),
              rate: h.bugRate,
              session: h.session,
            }));

            const pathD = points.reduce(
              (acc, pt, i) => `${acc} ${i === 0 ? 'M' : 'L'} ${pt.x} ${pt.y}`,
              ''
            );

            return (
              <g key={item.misconceptionId}>
                {/* Animated Connecting line */}
                <motion.path
                  d={pathD}
                  fill="none"
                  stroke={color}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 1 }}
                  transition={{ duration: 1.4, delay: 0.15 * mIdx, ease: 'easeOut' }}
                />

                {/* Animated Data points */}
                {points.map((pt, pIdx) => (
                  <motion.circle
                    key={`${item.misconceptionId}-pt-${pIdx}`}
                    cx={pt.x}
                    cy={pt.y}
                    r={hoveredPoint?.misconception === item.name && hoveredPoint?.session === pt.session ? 6.5 : 4.5}
                    fill={color}
                    stroke="#171A18"
                    strokeWidth="2"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.4 + 0.2 * pIdx, type: 'spring' }}
                    className="cursor-pointer"
                    onMouseEnter={() =>
                      setHoveredPoint({
                        misconception: item.name,
                        session: pt.session,
                        rate: pt.rate,
                        x: pt.x,
                        y: pt.y,
                      })
                    }
                    onMouseLeave={() => setHoveredPoint(null)}
                  />
                ))}
              </g>
            );
          })}
        </svg>

        {/* Floating Tooltip with AnimatePresence */}
        <AnimatePresence>
          {hoveredPoint && (
            <motion.div
              initial={{ opacity: 0, y: 5, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 5, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute z-20 pointer-events-none bg-[#1D221E] border border-[#353C36] rounded-xl p-3 shadow-2xl text-xs -translate-x-1/2 -translate-y-full mb-3 backdrop-blur-md"
              style={{
                left: `${(hoveredPoint.x / svgWidth) * 100}%`,
                top: `${(hoveredPoint.y / svgHeight) * 100}%`,
              }}
            >
              <p className="font-semibold text-[#F1F0E9]">{hoveredPoint.misconception}</p>
              <div className="flex items-center justify-between gap-4 text-[#B5B9B0] mt-1 font-mono">
                <span>{hoveredPoint.session}:</span>
                <span className="font-bold text-[#A3B5A0] tabular-nums">
                  {hoveredPoint.rate}% Error Rate
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Chart Legend */}
      <div className="mt-4 pt-4 border-t border-[#353C36] flex flex-wrap gap-4 items-center justify-center">
        {bugRates.map((item, mIdx) => {
          const color = colorPalette[mIdx % colorPalette.length];
          return (
            <motion.div
              key={item.misconceptionId}
              whileHover={{ scale: 1.05 }}
              className="flex items-center gap-2 text-xs cursor-default"
            >
              <span
                className="w-3 h-3 rounded-full shrink-0 shadow-sm"
                style={{ backgroundColor: color }}
              />
              <span className="text-[#B5B9B0]">{item.name}</span>
              <span className="font-mono text-[#F1F0E9] tabular-nums">
                ({item.currentBugRate}%)
              </span>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
