import React, { useEffect, useRef, useState } from 'react';

interface AcademicGlyph {
  id: number;
  symbol: string;
  x: number;
  y: number;
  size: number;
  delay: number;
  duration: number;
  color: string;
}

const GLYPH_SYMBOLS = ['π', '∑', '√', '∫', 'x²', '∞', 'Δ', 'θ', '≈', 'λ', '∂', 'Ω', '{ }', 'E=mc²'];
const GLYPH_COLORS = ['#A3B5A0', '#8FBF9B', '#B7C7B2', '#858D83'];

export const CinematicBackground: React.FC = () => {
  const [mousePos, setMousePos] = useState({ x: -500, y: -500 });
  const [glyphs, setGlyphs] = useState<AcademicGlyph[]>([]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const generated: AcademicGlyph[] = [];
    for (let i = 0; i < 16; i++) {
      generated.push({
        id: i,
        symbol: GLYPH_SYMBOLS[i % GLYPH_SYMBOLS.length],
        x: Math.random() * 95,
        y: Math.random() * 95,
        size: 12 + Math.random() * 10,
        delay: Math.random() * 6,
        duration: 10 + Math.random() * 6,
        color: GLYPH_COLORS[i % GLYPH_COLORS.length],
      });
    }
    setGlyphs(generated);

    let rafId: number;
    let targetX = -500;
    let targetY = -500;
    let currentX = -500;
    let currentY = -500;

    const handleMouseMove = (e: MouseEvent) => {
      targetX = e.clientX;
      targetY = e.clientY;
    };

    const updateGlow = () => {
      currentX += (targetX - currentX) * 0.08;
      currentY += (targetY - currentY) * 0.08;
      setMousePos({ x: currentX, y: currentY });
      rafId = requestAnimationFrame(updateGlow);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    rafId = requestAnimationFrame(updateGlow);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(rafId);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 pointer-events-none overflow-hidden z-0 select-none"
      aria-hidden="true"
    >
      {/* 1. Charcoal Base */}
      <div className="absolute inset-0 bg-[#171A18]" />

      {/* Atmospheric radial orbs - Muted Sage */}
      <div className="absolute -top-[20%] -left-[10%] w-[60vw] h-[60vw] max-w-[800px] max-h-[800px] rounded-full bg-gradient-to-br from-[#A3B5A0]/8 via-[#8FBF9B]/4 to-transparent blur-[140px] animate-float-gentle" />
      <div
        className="absolute top-[35%] -right-[15%] w-[55vw] h-[55vw] max-w-[750px] max-h-[750px] rounded-full bg-gradient-to-bl from-[#8FBF9B]/6 via-[#A3B5A0]/4 to-transparent blur-[140px] animate-float-gentle"
        style={{ animationDelay: '-4s' }}
      />
      <div
        className="absolute -bottom-[20%] left-[25%] w-[50vw] h-[50vw] max-w-[700px] max-h-[700px] rounded-full bg-gradient-to-tr from-[#1D221E] via-[#A3B5A0]/3 to-transparent blur-[120px] animate-pulse-subtle"
      />

      {/* 2. Soft Top Hairline */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-[#A3B5A0]/20 to-transparent" />

      {/* 3. 3D Perspective Grid in background */}
      <div className="absolute bottom-0 inset-x-0 h-[45vh] overflow-hidden opacity-15">
        <div
          className="w-full h-[200%] origin-bottom animate-grid-drift"
          style={{
            backgroundImage: `
              linear-gradient(to right, rgba(163, 181, 160, 0.08) 1px, transparent 1px),
              linear-gradient(to bottom, rgba(143, 191, 155, 0.05) 1px, transparent 1px)
            `,
            backgroundSize: '44px 44px',
            maskImage: 'linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.3) 40%, rgba(0,0,0,0) 90%)',
            WebkitMaskImage: 'linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.3) 40%, rgba(0,0,0,0) 90%)',
          }}
        />
      </div>

      {/* 4. Floating Academic Glyphs */}
      {glyphs.map((g) => (
        <span
          key={g.id}
          className="absolute font-mono font-bold animate-glyph pointer-events-none"
          style={{
            left: `${g.x}%`,
            top: `${g.y}%`,
            fontSize: `${g.size}px`,
            color: g.color,
            animationDelay: `${g.delay}s`,
            animationDuration: `${g.duration}s`,
            textShadow: `0 0 8px ${g.color}35`,
          }}
        >
          {g.symbol}
        </span>
      ))}

      {/* 5. Desktop Interactive Mouse-following Radial Glow */}
      <div
        className="hidden md:block absolute rounded-full pointer-events-none transform -translate-x-1/2 -translate-y-1/2 transition-opacity duration-300"
        style={{
          left: `${mousePos.x}px`,
          top: `${mousePos.y}px`,
          width: '450px',
          height: '450px',
          background: 'radial-gradient(circle, rgba(163, 181, 160, 0.06) 0%, rgba(143, 191, 155, 0.02) 45%, transparent 70%)',
          filter: 'blur(35px)',
        }}
      />
    </div>
  );
};
