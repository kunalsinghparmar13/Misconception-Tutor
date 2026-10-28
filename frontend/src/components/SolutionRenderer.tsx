import React, { useState } from 'react';
import { motion } from 'motion/react';
import {
  Check,
  Copy,
  Terminal,
  BookOpen,
  HelpCircle,
  Lightbulb,
  ExternalLink,
  Table as TableIcon,
  Calendar,
  Layers,
} from 'lucide-react';

interface SolutionRendererProps {
  content: string;
  subject?: string;
  steps?: string[];
  codeSnippet?: string;
  language?: string;
  takeaways?: string[];
  comparisonTable?: {
    headers: string[];
    rows: string[][];
  };
  timelineEvents?: {
    date: string;
    title: string;
    description: string;
  }[];
  className?: string;
}

export const SolutionRenderer: React.FC<SolutionRendererProps> = ({
  content,
  subject,
  steps,
  codeSnippet,
  language = 'python',
  takeaways,
  comparisonTable,
  timelineEvents,
  className = '',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Render markdown-like sections (headings, bold, lists, and code blocks)
  const renderFormattedMarkdown = (rawText: string) => {
    const lines = rawText.split('\n');
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeBuffer: string[] = [];
    let codeLang = '';

    lines.forEach((line, index) => {
      if (line.trim().startsWith('```')) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeLang = line.trim().replace('```', '') || 'code';
          codeBuffer = [];
        } else {
          inCodeBlock = false;
          const currentCode = codeBuffer.join('\n');
          elements.push(
            <div
              key={`code-${index}`}
              className="my-3 rounded-xl overflow-hidden border border-[#353C36] bg-[#121413] shadow-md"
            >
              <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#1A1E1B] border-b border-[#353C36] text-[11px] text-[#B5B9B0] font-mono">
                <span className="flex items-center gap-1.5 text-[#A3B5A0]">
                  <Terminal className="w-3.5 h-3.5" />
                  {codeLang}
                </span>
                <button
                  type="button"
                  onClick={() => handleCopyCode(currentCode)}
                  className="inline-flex items-center gap-1 hover:text-[#F1F0E9] transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-[#8FBF9B]" />
                      <span className="text-[#8FBF9B]">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-3.5 overflow-x-auto text-xs text-[#F1F0E9] font-mono leading-relaxed">
                <code>{currentCode}</code>
              </pre>
            </div>
          );
        }
        return;
      }

      if (inCodeBlock) {
        codeBuffer.push(line);
        return;
      }

      // Markdown Headings
      if (line.startsWith('### ')) {
        elements.push(
          <h3
            key={`h3-${index}`}
            className="text-base font-bold text-[#F1F0E9] mt-4 mb-2 flex items-center gap-2"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#A3B5A0]" />
            {line.replace('### ', '')}
          </h3>
        );
        return;
      }

      if (line.startsWith('#### ')) {
        elements.push(
          <h4
            key={`h4-${index}`}
            className="text-sm font-semibold text-[#A3B5A0] mt-3 mb-1.5"
          >
            {line.replace('#### ', '')}
          </h4>
        );
        return;
      }

      // Bullet lists
      if (line.trim().startsWith('- ') || line.trim().startsWith('* ')) {
        const bulletText = line.trim().substring(2);
        elements.push(
          <div
            key={`bullet-${index}`}
            className="flex items-start gap-2.5 my-1 text-xs text-[#B5B9B0] leading-relaxed pl-1"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-[#A3B5A0]/80 mt-1.5 shrink-0" />
            <span>{parseInlineStyles(bulletText)}</span>
          </div>
        );
        return;
      }

      // Numbered items
      if (/^\d+\.\s/.test(line.trim())) {
        const numText = line.trim().replace(/^\d+\.\s/, '');
        const numMatch = line.trim().match(/^(\d+)\./);
        const numStr = numMatch ? numMatch[1] : '1';
        elements.push(
          <div
            key={`num-${index}`}
            className="flex items-start gap-3 my-1.5 text-xs text-[#B5B9B0] leading-relaxed"
          >
            <span className="w-5 h-5 rounded-md bg-[#292F2A] border border-[#353C36] flex items-center justify-center font-mono text-[10px] text-[#A3B5A0] shrink-0 font-bold">
              {numStr}
            </span>
            <span className="pt-0.5">{parseInlineStyles(numText)}</span>
          </div>
        );
        return;
      }

      // Blank line spacer
      if (!line.trim()) {
        elements.push(<div key={`space-${index}`} className="h-2" />);
        return;
      }

      // Regular paragraph
      elements.push(
        <p key={`p-${index}`} className="text-xs text-[#B5B9B0] leading-relaxed my-1">
          {parseInlineStyles(line)}
        </p>
      );
    });

    return elements;
  };

  // Helper for inline bold, math, and code
  const parseInlineStyles = (text: string): React.ReactNode => {
    // Basic regex parser for **bold** and `code`
    const parts = text.split(/(\*\*.*?\*\*|`.*?`|\$\$.*?\$\$)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="text-[#F1F0E9] font-bold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={i}
            className="px-1.5 py-0.5 mx-0.5 rounded bg-[#1D221E] border border-[#353C36] font-mono text-[11px] text-[#A3B5A0]"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('$$') && part.endsWith('$$')) {
        return (
          <span
            key={i}
            className="px-2 py-0.5 mx-1 rounded bg-[#222823] border border-[#353C36] font-mono text-xs text-[#8FBF9B] inline-block"
          >
            {part.slice(2, -2)}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className={`space-y-4 text-left ${className}`}>
      {/* Main Content Body */}
      {content && (
        <div className="space-y-1 text-xs text-[#B5B9B0] leading-relaxed">
          {renderFormattedMarkdown(content)}
        </div>
      )}

      {/* Structured Numbered Steps if provided separately */}
      {steps && steps.length > 0 && (
        <div className="mt-4 p-4 rounded-2xl bg-[#1D221E] border border-[#353C36] space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#A3B5A0]">
            <BookOpen className="w-3.5 h-3.5" />
            <span>Structured Solution Protocol</span>
          </div>
          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-start gap-3">
                <span className="w-5 h-5 rounded-full bg-[#292F2A] border border-[#353C36] text-[10px] font-mono text-[#A3B5A0] flex items-center justify-center shrink-0 mt-0.5 font-bold">
                  {idx + 1}
                </span>
                <p className="text-xs text-[#B5B9B0] leading-relaxed">{step}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Standalone Code Snippet if supplied */}
      {codeSnippet && (
        <div className="rounded-xl overflow-hidden border border-[#353C36] bg-[#121413] shadow-md my-3">
          <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#1A1E1B] border-b border-[#353C36] text-[11px] text-[#B5B9B0] font-mono">
            <span className="flex items-center gap-1.5 text-[#A3B5A0]">
              <Terminal className="w-3.5 h-3.5" />
              {language}
            </span>
            <button
              type="button"
              onClick={() => handleCopyCode(codeSnippet)}
              className="inline-flex items-center gap-1 hover:text-[#F1F0E9] transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-[#8FBF9B]" />
                  <span className="text-[#8FBF9B]">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy Code</span>
                </>
              )}
            </button>
          </div>
          <pre className="p-3.5 overflow-x-auto text-xs text-[#F1F0E9] font-mono leading-relaxed">
            <code>{codeSnippet}</code>
          </pre>
        </div>
      )}

      {/* Comparison Table for Comparative Subjects */}
      {comparisonTable && (
        <div className="overflow-x-auto my-3 rounded-xl border border-[#353C36] bg-[#1D221E]">
          <div className="p-2.5 bg-[#222823] border-b border-[#353C36] flex items-center gap-1.5 text-xs font-semibold text-[#F1F0E9]">
            <TableIcon className="w-3.5 h-3.5 text-[#A3B5A0]" />
            <span>Comparative Analysis Matrix</span>
          </div>
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[#353C36] bg-[#292F2A]/60 text-[#A3B5A0] font-mono">
                {comparisonTable.headers.map((h, i) => (
                  <th key={i} className="p-2.5 font-semibold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparisonTable.rows.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className="border-b border-[#353C36]/50 hover:bg-[#222823] transition-colors"
                >
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} className="p-2.5 text-[#B5B9B0]">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Timeline Events for History & Temporal Subjects */}
      {timelineEvents && timelineEvents.length > 0 && (
        <div className="my-3 p-4 rounded-xl bg-[#1D221E] border border-[#353C36] space-y-3">
          <div className="flex items-center gap-1.5 text-xs font-semibold text-[#D8BC86]">
            <Calendar className="w-3.5 h-3.5" />
            <span>Chronological Causality Timeline</span>
          </div>
          <div className="relative border-l border-[#353C36] ml-2.5 pl-4 space-y-3.5">
            {timelineEvents.map((event, idx) => (
              <div key={idx} className="relative">
                <span className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-[#D8BC86] border-2 border-[#1D221E]" />
                <div className="text-[11px] font-mono text-[#D8BC86] font-semibold">{event.date}</div>
                <div className="text-xs font-bold text-[#F1F0E9]">{event.title}</div>
                <div className="text-[11px] text-[#858D83] leading-relaxed mt-0.5">{event.description}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Key Takeaways */}
      {takeaways && takeaways.length > 0 && (
        <div className="p-3.5 rounded-xl bg-[#283329]/60 border border-[#A3B5A0]/30 space-y-2">
          <div className="flex items-center gap-1.5 text-xs font-bold text-[#A3B5A0]">
            <Lightbulb className="w-3.5 h-3.5 text-[#A3B5A0]" />
            <span>Key Takeaways & Memory Anchors</span>
          </div>
          <ul className="space-y-1">
            {takeaways.map((item, i) => (
              <li key={i} className="text-xs text-[#B5B9B0] flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-[#A3B5A0] mt-1.5 shrink-0" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
