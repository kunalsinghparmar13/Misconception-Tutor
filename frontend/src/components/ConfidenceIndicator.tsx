import React from 'react';
import { motion } from 'motion/react';
import { AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';
import { AnimatedCounter } from './AnimatedCounter';

interface ConfidenceIndicatorProps {
  confidence: number; // 0.0 to 1.0
  isLowConfidence?: boolean;
  className?: string;
}

export const ConfidenceIndicator: React.FC<ConfidenceIndicatorProps> = ({
  confidence,
  isLowConfidence = false,
  className = '',
}) => {
  const percentage = Math.round(confidence * 100);

  // Confidence tiers
  const isHigh = percentage >= 80;
  const isMedium = percentage >= 60 && percentage < 80;
  const isUncertain = percentage < 60 || isLowConfidence;

  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-[#B5B9B0] font-medium flex items-center gap-1.5">
          {isUncertain ? (
            <AlertTriangle className="w-3.5 h-3.5 text-[#D8BC86]" />
          ) : isHigh ? (
            <CheckCircle className="w-3.5 h-3.5 text-[#8FBF9B]" />
          ) : (
            <ShieldAlert className="w-3.5 h-3.5 text-[#A3B5A0]" />
          )}
          <span>Diagnostic Confidence Index</span>
        </span>
        <span
          className={`font-mono font-semibold tabular-nums flex items-center gap-1 ${
            isUncertain
              ? 'text-[#D8BC86]'
              : isHigh
              ? 'text-[#8FBF9B]'
              : 'text-[#A3B5A0]'
          }`}
        >
          <AnimatedCounter value={percentage} suffix="%" />
          <span>{isUncertain ? '(Low Certainty)' : '(High Match)'}</span>
        </span>
      </div>

      {/* Animated Progress track */}
      <div className="w-full h-2 bg-[#171A18] rounded-full overflow-hidden border border-[#353C36] relative">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(5, percentage)}%` }}
          transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
          className={`h-full rounded-full relative ${
            isUncertain
              ? 'bg-[#D8BC86]'
              : isHigh
              ? 'bg-gradient-to-r from-[#283329] via-[#8FBF9B] to-[#A3B5A0]'
              : 'bg-[#A3B5A0]'
          }`}
        >
          <div className="absolute inset-0 bg-white/20 animate-pulse-subtle" />
        </motion.div>
      </div>

      <p className="text-[11px] text-[#858D83] leading-relaxed">
        {isUncertain
          ? 'Notice: Classifier confidence is under certainty threshold. System recommends additional practice probes before confirming this diagnosis.'
          : 'High probabilistic match: Error signature correlates with known pedagogical mental model patterns.'}
      </p>
    </div>
  );
};
