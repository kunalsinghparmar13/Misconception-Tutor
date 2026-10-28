import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ALL_SUBJECTS } from '../data/subjects';
import { DoubtConversation, DoubtMessage } from '../types/subjects';
import { aiService, BackendStatus } from '../services/aiService';
import { SolutionRenderer } from '../components/SolutionRenderer';
import {
  Send,
  Sparkles,
  Bot,
  User,
  RotateCcw,
  Plus,
  Terminal,
  Lightbulb,
  Copy,
  Check,
  BookOpen,
  ArrowRight,
  Flame,
  HelpCircle,
  Clock,
  Layers,
  ChevronDown,
  Volume2,
  VolumeX,
} from 'lucide-react';

interface DoubtSolverProps {
  initialSubjectId?: string;
  initialQuestion?: string;
}

const SAMPLE_QUESTIONS = [
  { subject: 'physics', text: 'Explain Newton\'s second law with real-world examples.' },
  { subject: 'history', text: 'Why did the French Revolution break out in 1789?' },
  { subject: 'biology', text: 'Explain cellular respiration vs photosynthesis in simple terms.' },
  { subject: 'mathematics', text: 'Solve this quadratic equation step by step: x² - 7x + 12 = 0' },
  { subject: 'programming', text: 'Debug my Python code: why does default list parameter share state?' },
  { subject: 'geography', text: 'Explain the difference between weather and climate.' },
];

export const DoubtSolver: React.FC<DoubtSolverProps> = ({
  initialSubjectId,
  initialQuestion,
}) => {
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>(initialSubjectId || 'all');
  const [inputText, setInputText] = useState(initialQuestion || '');
  const [codeSnippet, setCodeSnippet] = useState('');
  const [showCodeInput, setShowCodeInput] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [backendStatus, setBackendStatus] = useState<BackendStatus | null>(null);

  // Conversation Management
  const [conversations, setConversations] = useState<DoubtConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string>('default-conv');
  const [messages, setMessages] = useState<DoubtMessage[]>([]);
  const [speakingMessageId, setSpeakingMessageId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleSpeak = (messageId: string, rawText: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return;
    if (speakingMessageId === messageId) {
      window.speechSynthesis.cancel();
      setSpeakingMessageId(null);
      return;
    }
    window.speechSynthesis.cancel();
    const cleanSpeechText = rawText
      .replace(/```[\s\S]*?```/g, 'Code block omitted.')
      .replace(/[#*`_$~]/g, '')
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanSpeechText.slice(0, 1000));
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onend = () => setSpeakingMessageId(null);
    utterance.onerror = () => setSpeakingMessageId(null);
    setSpeakingMessageId(messageId);
    window.speechSynthesis.speak(utterance);
  };

  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  useEffect(() => {
    loadSavedConversations();
    checkBackend();
  }, []);

  const checkBackend = async () => {
    const status = await aiService.getBackendStatus();
    setBackendStatus(status);
  };

  const loadSavedConversations = () => {
    const stored = aiService.getStoredConversations();
    if (stored.length > 0) {
      setConversations(stored);
      setActiveConversationId(stored[0].id);
      setMessages(stored[0].messages);
      setSelectedSubjectId(stored[0].subjectId || 'all');
    } else {
      // Create initial conversation
      const welcomeConv: DoubtConversation = {
        id: `conv-${Date.now()}`,
        title: 'New Doubt Session',
        subjectId: selectedSubjectId,
        messages: [
          {
            id: 'msg-welcome',
            role: 'assistant',
            content: `### Welcome to the All-Subject AI Doubt Solver! 🎓\n\nI can help you understand concepts, solve numerical problems, debug code, analyze historical events, or verify grammar across **all major subjects**.\n\n**Quick Tips:**\n- Ask naturally: *"Why is the sky blue?"* or *"How to balance redox reactions?"*\n- Click **Paste Code** to debug Python, C++, Java, or JS.\n- Use the one-click refinement buttons for **Simpler explanations**, **Deeper math**, or **Step-by-step solutions**!`,
            timestamp: new Date().toISOString(),
          },
        ],
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      setConversations([welcomeConv]);
      setActiveConversationId(welcomeConv.id);
      setMessages(welcomeConv.messages);
      aiService.saveConversation(welcomeConv);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleStartNewChat = () => {
    const newConv: DoubtConversation = {
      id: `conv-${Date.now()}`,
      title: 'New Session',
      subjectId: selectedSubjectId,
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: `New session started. How can I assist you in **${
            ALL_SUBJECTS.find((s) => s.id === selectedSubjectId)?.name || 'any subject'
          }** today?`,
          timestamp: new Date().toISOString(),
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const updated = [newConv, ...conversations];
    setConversations(updated);
    setActiveConversationId(newConv.id);
    setMessages(newConv.messages);
    aiService.saveConversation(newConv);
  };

  const handleSelectConversation = (conv: DoubtConversation) => {
    setActiveConversationId(conv.id);
    setMessages(conv.messages);
    setSelectedSubjectId(conv.subjectId || 'all');
  };

  const handleSend = async (customPrompt?: string, mode: 'normal' | 'simpler' | 'deeper' | 'step-by-step' | 'analogy' | 'code-debug' | 'summary' = 'normal') => {
    const query = customPrompt || inputText;
    if (!query.trim() && !codeSnippet.trim()) return;

    const userMessage: DoubtMessage = {
      id: `msg-user-${Date.now()}`,
      role: 'user',
      content: query.trim(),
      subjectId: selectedSubjectId,
      codeSnippet: codeSnippet.trim() || undefined,
      timestamp: new Date().toISOString(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputText('');
    const sentCode = codeSnippet;
    setCodeSnippet('');
    setShowCodeInput(false);
    setIsLoading(true);

    try {
      const subjectObj = ALL_SUBJECTS.find((s) => s.id === selectedSubjectId);
      const subjectLabel = subjectObj ? subjectObj.name : 'Universal';

      const historyContext = updatedMessages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const result = await aiService.askDoubt({
        subject: subjectLabel,
        question: query,
        codeSnippet: sentCode || undefined,
        mode,
        history: historyContext,
      });

      const aiMessage: DoubtMessage = {
        id: `msg-ai-${Date.now()}`,
        role: 'assistant',
        content: result.answer,
        subjectId: selectedSubjectId,
        timestamp: new Date().toISOString(),
      };

      const finalMessages = [...updatedMessages, aiMessage];
      setMessages(finalMessages);

      // Update current conversation
      const activeConv = conversations.find((c) => c.id === activeConversationId);
      if (activeConv) {
        const title = activeConv.title === 'New Session' || activeConv.title === 'New Doubt Session'
          ? query.slice(0, 32) + (query.length > 32 ? '...' : '')
          : activeConv.title;
        const updatedConv: DoubtConversation = {
          ...activeConv,
          title,
          messages: finalMessages,
          updatedAt: new Date().toISOString(),
        };
        aiService.saveConversation(updatedConv);
        setConversations(conversations.map((c) => (c.id === updatedConv.id ? updatedConv : c)));
      }
    } catch (err: any) {
      const errorMessage: DoubtMessage = {
        id: `msg-err-${Date.now()}`,
        role: 'assistant',
        content: `**Service Notice:** ${err.message || 'Unable to process doubt query at this time. Please try again.'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages([...updatedMessages, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefinement = (mode: 'simpler' | 'deeper' | 'step-by-step' | 'analogy' | 'code-debug' | 'summary') => {
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (!lastUserMsg) return;

    let prompt = '';
    switch (mode) {
      case 'simpler':
        prompt = `Can you explain that in much simpler terms for a beginner?`;
        break;
      case 'deeper':
        prompt = `Could you provide a deeper, mathematically and scientifically rigorous explanation?`;
        break;
      case 'step-by-step':
        prompt = `Please break down the step-by-step solution protocol for this.`;
        break;
      case 'analogy':
        prompt = `Give me an intuitive real-world analogy to remember this concept.`;
        break;
      case 'summary':
        prompt = `Summarize the essential rules and key formulas in bullet points.`;
        break;
      case 'code-debug':
        prompt = `Can you show the exact corrected code implementation with comments?`;
        break;
    }
    handleSend(prompt, mode);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[#222823] via-[#1D221E] to-[#171A18] border border-[#353C36] p-6 lg:p-8 backdrop-blur-xl shadow-xl">
        <div className="absolute top-0 right-0 w-80 h-80 bg-[#A3B5A0]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#283329] border border-[#A3B5A0]/30 text-xs font-semibold text-[#A3B5A0]">
              <Sparkles className="w-3.5 h-3.5 text-[#A3B5A0]" />
              <span>Universal Academic Doubt Resolution Engine</span>
            </div>
            <h1 className="text-3xl font-extrabold text-[#F1F0E9] tracking-tight">
              AI Doubt Solver &{' '}
              <span className="bg-gradient-to-r from-[#A3B5A0] to-[#B7C7B2] bg-clip-text text-transparent">
                Concept Explainer
              </span>
            </h1>
            <p className="text-sm text-[#B5B9B0] max-w-xl">
              Ask any question across STEM, Programming, Humanities, Commerce, or Languages.
              Get tailored explanations, formulas, code fixes, and verified historical timelines.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="px-3.5 py-2 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs flex items-center gap-2">
              <span
                className={`w-2 h-2 rounded-full ${
                  backendStatus?.liveAiEnabled ? 'bg-[#8FBF9B] animate-pulse' : 'bg-[#D8BC86]'
                }`}
              />
              <span className="text-[#B5B9B0] text-[11px]">
                {backendStatus?.liveAiEnabled ? 'Live Gemini 3.8 Flash' : 'Pedagogical Engine Active'}
              </span>
            </div>
            <button
              onClick={handleStartNewChat}
              className="px-4 py-2.5 rounded-xl bg-[#A3B5A0] hover:bg-[#B7C7B2] text-[#171A18] font-bold text-xs flex items-center gap-1.5 shadow-md transition-all shrink-0"
            >
              <Plus className="w-4 h-4" />
              <span>New Doubt Session</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout: History Drawer + Chat Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Subject Selector & Recent Sessions */}
        <div className="lg:col-span-4 space-y-4">
          {/* Subject Filter Card */}
          <div className="p-4 rounded-2xl bg-[#222823] border border-[#353C36] space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold text-[#F1F0E9]">
              <span className="flex items-center gap-1.5 text-[#A3B5A0]">
                <Layers className="w-3.5 h-3.5" />
                Active Subject Context
              </span>
              <span className="text-[10px] text-[#858D83]">Tailors explanations</span>
            </div>

            <select
              value={selectedSubjectId}
              onChange={(e) => setSelectedSubjectId(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl bg-[#1D221E] border border-[#353C36] text-xs text-[#F1F0E9] focus:border-[#A3B5A0] focus:outline-none"
            >
              <option value="all">Universal (Auto-Detect Subject)</option>
              {ALL_SUBJECTS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.categoryLabel})
                </option>
              ))}
            </select>
          </div>

          {/* Quick Examples Inspiration */}
          <div className="p-4 rounded-2xl bg-[#222823] border border-[#353C36] space-y-3">
            <div className="text-xs font-semibold text-[#F1F0E9] flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-[#D8BC86]" />
              <span>Example Queries</span>
            </div>
            <div className="space-y-1.5">
              {SAMPLE_QUESTIONS.map((ex, idx) => (
                <button
                  key={idx}
                  onClick={() => {
                    setSelectedSubjectId(ex.subject);
                    setInputText(ex.text);
                  }}
                  className="w-full text-left p-2.5 rounded-xl bg-[#1D221E] hover:bg-[#292F2A] border border-[#353C36]/50 hover:border-[#A3B5A0]/40 text-[11px] text-[#B5B9B0] hover:text-[#F1F0E9] transition-all line-clamp-2"
                >
                  "{ex.text}"
                </button>
              ))}
            </div>
          </div>

          {/* Session History Sidebar */}
          <div className="p-4 rounded-2xl bg-[#222823] border border-[#353C36] space-y-3">
            <div className="flex items-center justify-between text-xs font-semibold text-[#F1F0E9]">
              <span className="flex items-center gap-1.5 text-[#B5B9B0]">
                <Clock className="w-3.5 h-3.5" />
                Previous Conversations
              </span>
              <span className="text-[10px] text-[#858D83] font-mono">{conversations.length}</span>
            </div>

            <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
              {conversations.map((c) => (
                <button
                  key={c.id}
                  onClick={() => handleSelectConversation(c)}
                  className={`w-full text-left p-2.5 rounded-xl text-xs transition-all flex items-center justify-between ${
                    c.id === activeConversationId
                      ? 'bg-[#283329] text-[#A3B5A0] border border-[#A3B5A0]/40 font-semibold'
                      : 'bg-[#1D221E] text-[#B5B9B0] hover:bg-[#292F2A] border border-[#353C36]/50'
                  }`}
                >
                  <span className="truncate flex-1 mr-2">{c.title}</span>
                  <span className="text-[10px] text-[#858D83] font-mono shrink-0">
                    {new Date(c.updatedAt).toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' })}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Chat Feed & Action Bar */}
        <div className="lg:col-span-8 space-y-4">
          <div className="p-4 sm:p-6 rounded-3xl bg-[#222823] border border-[#353C36] min-h-[520px] flex flex-col justify-between shadow-xl">
            {/* Messages Feed */}
            <div className="space-y-4 overflow-y-auto max-h-[580px] pr-2">
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex gap-3 ${
                    msg.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-xl bg-[#283329] border border-[#A3B5A0]/30 flex items-center justify-center text-[#A3B5A0] shrink-0 mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl p-4 sm:p-5 shadow-sm text-left ${
                      msg.role === 'user'
                        ? 'bg-[#292F2A] border border-[#353C36] text-[#F1F0E9]'
                        : 'bg-[#1D221E] border border-[#353C36] text-[#B5B9B0]'
                    }`}
                  >
                    {msg.role === 'user' ? (
                      <div className="space-y-2">
                        <p className="text-xs sm:text-sm text-[#F1F0E9] whitespace-pre-wrap">
                          {msg.content}
                        </p>
                        {msg.codeSnippet && (
                          <pre className="p-2.5 rounded-lg bg-[#121413] border border-[#353C36] text-[11px] font-mono text-[#A3B5A0] overflow-x-auto">
                            <code>{msg.codeSnippet}</code>
                          </pre>
                        )}
                      </div>
                    ) : (
                      <SolutionRenderer
                        content={msg.content}
                        subject={selectedSubjectId}
                      />
                    )}

                    <div className="mt-2 flex items-center justify-between text-[10px] text-[#858D83]">
                      <span>{new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      {msg.role === 'assistant' && (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleSpeak(msg.id, msg.content)}
                            className={`flex items-center gap-1 transition-colors px-2 py-0.5 rounded-md ${
                              speakingMessageId === msg.id
                                ? 'bg-[#A3B5A0]/20 text-[#A3B5A0] font-semibold'
                                : 'hover:text-[#F1F0E9]'
                            }`}
                            title={speakingMessageId === msg.id ? 'Stop reading' : 'Read explanation aloud'}
                          >
                            {speakingMessageId === msg.id ? (
                              <>
                                <VolumeX className="w-3 h-3 text-[#D98E8E]" />
                                <span className="text-[#D98E8E]">Stop</span>
                              </>
                            ) : (
                              <>
                                <Volume2 className="w-3 h-3 text-[#A3B5A0]" />
                                <span>Listen</span>
                              </>
                            )}
                          </button>
                          <button
                            type="button"
                            onClick={() => navigator.clipboard.writeText(msg.content)}
                            className="hover:text-[#F1F0E9] flex items-center gap-1 transition-colors"
                          >
                            <Copy className="w-3 h-3" />
                            <span>Copy</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>

                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-xl bg-[#343E34] border border-[#353C36] flex items-center justify-center text-[#F1F0E9] shrink-0 mt-1">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </motion.div>
              ))}

              {isLoading && (
                <div className="flex gap-3 items-center text-xs text-[#A3B5A0] p-4 rounded-2xl bg-[#1D221E] border border-[#353C36] w-fit">
                  <div className="w-4 h-4 border-2 border-[#A3B5A0] border-t-transparent rounded-full animate-spin" />
                  <span className="animate-pulse">Formulating pedagogical response across subject knowledge graph...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Quick Refinement Action Pills */}
            <div className="pt-4 border-t border-[#353C36] space-y-3">
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
                <span className="text-[11px] text-[#858D83] uppercase font-semibold shrink-0">Refine:</span>
                <button
                  onClick={() => handleRefinement('simpler')}
                  disabled={isLoading || messages.length <= 1}
                  className="px-2.5 py-1 rounded-lg bg-[#1D221E] hover:bg-[#292F2A] border border-[#353C36] text-[11px] text-[#A3B5A0] hover:text-[#F1F0E9] shrink-0 transition-colors disabled:opacity-40"
                >
                  💡 Simpler Explanation
                </button>
                <button
                  onClick={() => handleRefinement('step-by-step')}
                  disabled={isLoading || messages.length <= 1}
                  className="px-2.5 py-1 rounded-lg bg-[#1D221E] hover:bg-[#292F2A] border border-[#353C36] text-[11px] text-[#A3B5A0] hover:text-[#F1F0E9] shrink-0 transition-colors disabled:opacity-40"
                >
                  🔢 Step-by-Step Solution
                </button>
                <button
                  onClick={() => handleRefinement('analogy')}
                  disabled={isLoading || messages.length <= 1}
                  className="px-2.5 py-1 rounded-lg bg-[#1D221E] hover:bg-[#292F2A] border border-[#353C36] text-[11px] text-[#A3B5A0] hover:text-[#F1F0E9] shrink-0 transition-colors disabled:opacity-40"
                >
                  🌱 Give Analogy
                </button>
                <button
                  onClick={() => handleRefinement('deeper')}
                  disabled={isLoading || messages.length <= 1}
                  className="px-2.5 py-1 rounded-lg bg-[#1D221E] hover:bg-[#292F2A] border border-[#353C36] text-[11px] text-[#A3B5A0] hover:text-[#F1F0E9] shrink-0 transition-colors disabled:opacity-40"
                >
                  🔬 In-Depth Theory
                </button>
                <button
                  onClick={() => handleRefinement('summary')}
                  disabled={isLoading || messages.length <= 1}
                  className="px-2.5 py-1 rounded-lg bg-[#1D221E] hover:bg-[#292F2A] border border-[#353C36] text-[11px] text-[#A3B5A0] hover:text-[#F1F0E9] shrink-0 transition-colors disabled:opacity-40"
                >
                  📋 Key Takeaways
                </button>
              </div>

              {/* Code Snippet Drawer Toggle */}
              {showCodeInput && (
                <div className="p-3 rounded-xl bg-[#121413] border border-[#353C36] space-y-2">
                  <div className="flex items-center justify-between text-xs text-[#A3B5A0]">
                    <span className="flex items-center gap-1 font-mono">
                      <Terminal className="w-3.5 h-3.5" /> Code to Debug / Explain:
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowCodeInput(false)}
                      className="text-[#858D83] hover:text-[#F1F0E9]"
                    >
                      Hide
                    </button>
                  </div>
                  <textarea
                    rows={4}
                    value={codeSnippet}
                    onChange={(e) => setCodeSnippet(e.target.value)}
                    placeholder="Paste your Python, JS, C++, SQL, or Java code here..."
                    className="w-full p-2.5 rounded-lg bg-[#1D221E] border border-[#353C36] text-xs font-mono text-[#F1F0E9] placeholder-[#858D83] focus:border-[#A3B5A0] focus:outline-none"
                  />
                </div>
              )}

              {/* Input Area */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowCodeInput(!showCodeInput)}
                  className={`p-3 rounded-xl border text-xs flex items-center gap-1.5 transition-colors shrink-0 ${
                    showCodeInput
                      ? 'bg-[#283329] border-[#A3B5A0] text-[#A3B5A0]'
                      : 'bg-[#1D221E] border-[#353C36] text-[#B5B9B0] hover:text-[#F1F0E9]'
                  }`}
                  title="Attach code snippet"
                >
                  <Terminal className="w-4 h-4" />
                  <span className="hidden sm:inline">Code</span>
                </button>

                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  disabled={isLoading}
                  placeholder={`Ask a doubt in ${ALL_SUBJECTS.find((s) => s.id === selectedSubjectId)?.name || 'any subject'}...`}
                  className="flex-1 px-4 py-3 rounded-xl bg-[#1D221E] border border-[#353C36] focus:border-[#A3B5A0] focus:ring-2 focus:ring-[#A3B5A0]/20 text-xs sm:text-sm text-[#F1F0E9] placeholder-[#858D83] focus:outline-none transition-all"
                />

                <button
                  type="button"
                  onClick={() => handleSend()}
                  disabled={isLoading || (!inputText.trim() && !codeSnippet.trim())}
                  className={`p-3 rounded-xl font-bold text-xs flex items-center justify-center transition-all ${
                    (inputText.trim() || codeSnippet.trim()) && !isLoading
                      ? 'bg-[#A3B5A0] text-[#171A18] hover:bg-[#B7C7B2] shadow-md shadow-[#A3B5A0]/20'
                      : 'bg-[#292F2A] text-[#858D83] cursor-not-allowed border border-[#353C36]'
                  }`}
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
