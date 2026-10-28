import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { Sparkles, Brain, Cpu, Search } from 'lucide-react';

interface AiAnalysisScannerProps {
  onComplete?: () => void;
  duration?: number; // ms
}

const STAGES = [
  { icon: Search, text: 'Scanning question components and student reasoning...' },
  { icon: Cpu, text: 'Deconstructing submitted problem-solving steps...' },
  { icon: Brain, text: 'Correlating with academic error taxonomy & misconceptions...' },
  { icon: Sparkles, text: 'Synthesizing targeted cognitive guidance...' },
];

export const AiAnalysisScanner: React.FC<AiAnalysisScannerProps> = ({
  onComplete,
  duration = 2400,
}) => {
  const [stageIndex, setStageIndex] = useState<number>(0);

  useEffect(() => {
    const stepDuration = duration / STAGES.length;
    const interval = setInterval(() => {
      setStageIndex((prev) => {
        if (prev < STAGES.length - 1) {
          return prev + 1;
        }
        clearInterval(interval);
        return prev;
      });
    }, stepDuration);

    const finishTimer = setTimeout(() => {
      if (onComplete) onComplete();
    }, duration);

    return () => {
      clearInterval(interval);
      clearTimeout(finishTimer);
    };
  }, [duration, onComplete]);

  const CurrentIcon = STAGES[stageIndex].icon;

  return (
    <div className="relative rounded-3xl bg-[#222823] border border-[#353C36] p-8 md:p-12 text-center overflow-hidden shadow-2xl backdrop-blur-xl">
      {/* 1. Animated Horizontal Scanning Laser Line in Muted Sage */}
      <div className="absolute inset-x-0 h-1 bg-gradient-to-r from-transparent via-[#A3B5A0] to-transparent shadow-[0_0_15px_#A3B5A0] animate-laser-scan pointer-events-none" />

      {/* 2. Central Pulsing Neural Core */}
      <div className="relative z-10 flex flex-col items-center max-w-md mx-auto space-y-6">
        <div className="relative w-20 h-20 flex items-center justify-center">
          {/* Orbital pulsing rings */}
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-[#A3B5A0]/30"
            animate={{ scale: [1, 1.25, 1], opacity: [0.6, 0.2, 0.6] }}
            transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.div
            className="absolute inset-2 rounded-full border border-[#8FBF9B]/35"
            animate={{ rotate: 360 }}
            transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
          />

          <div className="w-14 h-14 rounded-2xl bg-[#283329] border border-[#A3B5A0]/40 flex items-center justify-center text-[#A3B5A0] shadow-md shadow-[#A3B5A0]/15">
            <CurrentIcon className="w-7 h-7 animate-pulse" />
          </div>
        </div>

        {/* 3. Dynamic Analysis Phase Text */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
            <Sparkles className="w-3.5 h-3.5 animate-spin" style={{ animationDuration: '3s' }} />
            <span>AI Cognitive Diagnostic Scan Active</span>
          </div>
          <h3 className="text-lg md:text-xl font-bold text-[#F1F0E9] tracking-tight">
            {STAGES[stageIndex].text}
          </h3>
          <p className="text-xs text-[#B5B9B0]">
            Evaluating student calculations against discipline misconception patterns
          </p>
        </div>

        {/* 4. Progress Stepper Dots */}
        <div className="flex items-center gap-2 pt-2">
          {STAGES.map((_, idx) => (
            <div
              key={idx}
              className={`h-1.5 rounded-full transition-all duration-300 ${
                idx === stageIndex
                  ? 'w-8 bg-[#A3B5A0]'
                  : idx < stageIndex
                  ? 'w-3 bg-[#8FBF9B]'
                  : 'w-2 bg-[#353C36]'
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
