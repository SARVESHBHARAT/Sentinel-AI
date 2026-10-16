import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronLeft,
  ChevronRight,
  Pause,
  Play,
  ArrowUpRight,
  ShieldAlert,
  AlertTriangle,
  Flame,
  BrainCircuit,
  Lock,
  Scale,
} from 'lucide-react';

interface IncidentStory {
  id: string;
  incidentId: string;
  category: string;
  severity: 'critical' | 'high' | 'medium';
  title: string;
  model: string;
  provider: string;
  summary: string;
  impact: string;
  riskScore: number;
  icon: typeof ShieldAlert;
  accentColor: string;
}

const STORIES: IncidentStory[] = [
  {
    id: 'story-1',
    incidentId: 'INC-2026-0149',
    category: 'Security Vulnerability',
    severity: 'critical',
    title: 'Prompt Injection Bypasses Customer Support Guardrails',
    model: 'Qwen 2.5',
    provider: 'Qwen',
    summary:
      'Adversarial markdown injection forced the customer assistant to escape system instructions and expose internal microservice endpoints.',
    impact: 'Live customer chat leaked back-office database schemas and administrative API authorization headers.',
    riskScore: 94,
    icon: Lock,
    accentColor: '#ef4444',
  },
  {
    id: 'story-2',
    incidentId: 'INC-2026-0151',
    category: 'Privacy / Data Leakage',
    severity: 'high',
    title: 'Cross-Tenant PII Memorization in Financial Copilot',
    model: 'GPT-4o',
    provider: 'OpenAI',
    summary:
      'Shared attention state and caching in multi-tenant financial reporting emitted confidential corporate tax identifiers into a competitor’s session.',
    impact: 'Cross-tenant session state bleed compromised sensitive accounting records for 3 enterprise clients.',
    riskScore: 88,
    icon: ShieldAlert,
    accentColor: '#f97316',
  },
  {
    id: 'story-3',
    incidentId: 'INC-2026-0155',
    category: 'Harmful Output',
    severity: 'critical',
    title: 'Multi-Turn Context Shift Overrides Safety Filters',
    model: 'Gemini 1.5 Pro',
    provider: 'Google',
    summary:
      'Gradual persona adoption across multi-step dialogue bypassed automated content moderation to produce hazardous chemical compound blueprints.',
    impact: 'Systemic moderation evasion allowed high-risk procedural synthesis under fictional framing.',
    riskScore: 92,
    icon: Flame,
    accentColor: '#ef4444',
  },
  {
    id: 'story-4',
    incidentId: 'INC-2026-0153',
    category: 'Bias / Discrimination',
    severity: 'high',
    title: 'Systemic Screening Disparities in Automated Hiring Engine',
    model: 'Mistral Large',
    provider: 'Mistral',
    summary:
      'An enterprise talent assessment agent systematically depressed suitability scores for candidates with non-Western naming patterns.',
    impact: 'Over 12,000 applicant evaluations experienced unjustified ranking penalties before detection.',
    riskScore: 82,
    icon: Scale,
    accentColor: '#f97316',
  },
  {
    id: 'story-5',
    incidentId: 'INC-2026-0148',
    category: 'Hallucination / Misinformation',
    severity: 'high',
    title: 'Fabricated Case Precedents in Legal Document Analysis',
    model: 'GPT-4o',
    provider: 'OpenAI',
    summary:
      'Corporate contract review assistant hallucinated non-existent appellate rulings and incorrect statutory deadlines in formal legal filings.',
    impact: 'Enterprise customer missed statutory appeal window due to fictional jurisdiction precedents.',
    riskScore: 85,
    icon: BrainCircuit,
    accentColor: '#eab308',
  },
  {
    id: 'story-6',
    incidentId: 'INC-2026-0160',
    category: 'Reliability Failure',
    severity: 'medium',
    title: 'Autonomous Classification Quarantines Legitimate Invoices',
    model: 'GPT-4o',
    provider: 'OpenAI',
    summary:
      'Edge invoice processing model misclassified high-value legitimate vendor billing emails as sophisticated credential phishing attempts.',
    impact: 'Critical supplier accounts frozen during quarter-end settlement, delaying logistics operations.',
    riskScore: 68,
    icon: AlertTriangle,
    accentColor: '#38bdf8',
  },
];

export default function IncidentStoriesCarousel() {
  const navigate = useNavigate();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isHovered, setIsHovered] = useState(false);
  const [isPlaying, setIsPlaying] = useState(true);
  const [visibleCount, setVisibleCount] = useState(3);
  const [direction, setDirection] = useState<'next' | 'prev'>('next');

  // Check prefers-reduced-motion
  const prefersReducedMotion =
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false;

  // Responsive visible count tracking
  useEffect(() => {
    const updateVisibleCount = () => {
      const width = window.innerWidth;
      if (width < 680) {
        setVisibleCount(1);
      } else if (width < 1024) {
        setVisibleCount(2);
      } else {
        setVisibleCount(3);
      }
    };

    updateVisibleCount();
    window.addEventListener('resize', updateVisibleCount);
    return () => window.removeEventListener('resize', updateVisibleCount);
  }, []);

  const handleNext = useCallback(() => {
    setDirection('next');
    setCurrentIndex((prev) => (prev + 1) % STORIES.length);
  }, []);

  const handlePrev = useCallback(() => {
    setDirection('prev');
    setCurrentIndex((prev) => (prev - 1 + STORIES.length) % STORIES.length);
  }, []);

  // Auto-rotation every 6 seconds (between 5-7s)
  useEffect(() => {
    if (!isPlaying || isHovered || prefersReducedMotion) {
      return;
    }

    const timer = setInterval(() => {
      handleNext();
    }, 6000);

    return () => clearInterval(timer);
  }, [isPlaying, isHovered, prefersReducedMotion, handleNext]);

  // Compute the visible items based on current index and visibleCount
  const visibleStories = Array.from({ length: visibleCount }).map((_, i) => {
    const idx = (currentIndex + i) % STORIES.length;
    return { story: STORIES[idx], slotIndex: i };
  });

  return (
    <section
      style={{
        background: 'var(--bg-deep)',
        borderTop: '1px solid var(--border-subtle)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '5rem 2rem',
        position: 'relative',
        overflow: 'hidden',
      }}
      aria-label="AI Incident Stories"
    >
      {/* Background radial accent glow */}
      <div
        style={{
          position: 'absolute',
          top: '20%',
          left: '50%',
          transform: 'translateX(-50%)',
          width: '700px',
          height: '350px',
          background: 'radial-gradient(circle, rgba(56, 189, 248, 0.04) 0%, rgba(239, 68, 68, 0.02) 40%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      <div className="container" style={{ position: 'relative', zIndex: 1 }}>
        {/* Section Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            flexWrap: 'wrap',
            gap: '1.5rem',
            marginBottom: '2.5rem',
          }}
        >
          <div>
            <div
              className="page-eyebrow"
              style={{
                marginBottom: '0.5rem',
                color: 'var(--accent-cyan)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: 'var(--accent-cyan)',
                  boxShadow: '0 0 8px var(--accent-cyan)',
                }}
              />
              WHERE AI GETS IT WRONG
            </div>
            <h2 style={{ letterSpacing: '-0.03em', margin: '0 0 0.5rem 0' }}>
              AI Incident Stories
            </h2>
            <p
              style={{
                fontSize: '0.95rem',
                color: 'var(--text-secondary)',
                margin: 0,
                maxWidth: '620px',
                lineHeight: 1.5,
              }}
            >
              Real-world breakdown of model failures, autonomous agent bypasses, and safety
              vulnerabilities captured across production deployments.
            </p>
          </div>

          {/* Interactive Controls */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.625rem',
              flexShrink: 0,
            }}
          >
            {/* Play/Pause toggle */}
            <button
              onClick={() => setIsPlaying((p) => !p)}
              className="btn btn-secondary btn-sm"
              style={{
                padding: '0.45rem 0.75rem',
                fontSize: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                fontFamily: 'var(--font-mono)',
              }}
              title={isPlaying ? 'Pause carousel rotation' : 'Resume carousel rotation'}
              aria-label={isPlaying ? 'Pause rotation' : 'Resume rotation'}
            >
              {isPlaying ? <Pause size={13} /> : <Play size={13} />}
              <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
            </button>

            {/* Previous Button */}
            <button
              onClick={handlePrev}
              className="btn btn-secondary btn-sm"
              style={{
                padding: '0.45rem 0.6rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              aria-label="Previous incident story"
            >
              <ChevronLeft size={16} />
            </button>

            {/* Next Button */}
            <button
              onClick={handleNext}
              className="btn btn-secondary btn-sm"
              style={{
                padding: '0.45rem 0.6rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
              aria-label="Next incident story"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* Carousel Viewport & Cards */}
        <div
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          style={{
            position: 'relative',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${visibleCount}, minmax(0, 1fr))`,
              gap: '1.25rem',
            }}
          >
            <AnimatePresence mode="popLayout" initial={false}>
              {visibleStories.map(({ story, slotIndex }) => {
                const IconComponent = story.icon;
                const severityBadgeClass =
                  story.severity === 'critical'
                    ? 'badge-critical'
                    : story.severity === 'high'
                    ? 'badge-high'
                    : 'badge-medium';

                return (
                  <motion.div
                    key={`${story.id}-${slotIndex}-${currentIndex}`}
                    initial={
                      prefersReducedMotion
                        ? { opacity: 0 }
                        : {
                            opacity: 0,
                            x: direction === 'next' ? 24 : -24,
                            scale: 0.98,
                          }
                    }
                    animate={{
                      opacity: 1,
                      x: 0,
                      scale: 1,
                      transition: {
                        duration: prefersReducedMotion ? 0.2 : 0.45,
                        ease: [0.16, 1, 0.3, 1],
                      },
                    }}
                    exit={
                      prefersReducedMotion
                        ? { opacity: 0 }
                        : {
                            opacity: 0,
                            x: direction === 'next' ? -24 : 24,
                            scale: 0.98,
                            transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] },
                          }
                    }
                    className="card"
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                      padding: '1.5rem',
                      background: 'rgba(16, 16, 16, 0.85)',
                      border: '1px solid var(--border-default)',
                      borderRadius: 14,
                      position: 'relative',
                      backdropFilter: 'blur(10px)',
                      cursor: 'pointer',
                      transition: 'border-color 0.25s ease, box-shadow 0.25s ease, transform 0.2s ease',
                      minHeight: '380px',
                    }}
                    onClick={() => navigate(`/incidents/${story.incidentId}`)}
                    whileHover={{
                      y: -4,
                      borderColor: story.accentColor,
                      boxShadow: `0 8px 30px ${story.accentColor}18`,
                    }}
                  >
                    {/* Top Row: Category + Severity Badges */}
                    <div>
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          gap: '0.5rem',
                          marginBottom: '1rem',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                          <span
                            style={{
                              width: 28,
                              height: 28,
                              borderRadius: 8,
                              background: `${story.accentColor}15`,
                              border: `1px solid ${story.accentColor}30`,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              color: story.accentColor,
                              flexShrink: 0,
                            }}
                          >
                            <IconComponent size={15} />
                          </span>
                          <span
                            style={{
                              fontFamily: 'var(--font-mono)',
                              fontSize: '0.7rem',
                              color: 'var(--text-muted)',
                              letterSpacing: '0.04em',
                            }}
                          >
                            {story.incidentId}
                          </span>
                        </div>
                        <span className={`badge ${severityBadgeClass}`} style={{ fontSize: '0.65rem' }}>
                          {story.severity.toUpperCase()}
                        </span>
                      </div>

                      {/* Model & Provider metadata */}
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          fontSize: '0.75rem',
                          color: 'var(--accent-cyan)',
                          fontFamily: 'var(--font-mono)',
                          marginBottom: '0.75rem',
                        }}
                      >
                        <span>{story.model}</span>
                        <span style={{ color: 'var(--border-default)' }}>·</span>
                        <span style={{ color: 'var(--text-muted)' }}>{story.provider}</span>
                      </div>

                      {/* Story Headline */}
                      <h4
                        style={{
                          fontSize: '1.05rem',
                          fontWeight: 600,
                          lineHeight: 1.35,
                          marginBottom: '0.75rem',
                          color: 'var(--text-primary)',
                          letterSpacing: '-0.02em',
                        }}
                      >
                        {story.title}
                      </h4>

                      {/* Story Summary Narrative */}
                      <p
                        style={{
                          fontSize: '0.825rem',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.55,
                          margin: '0 0 1rem 0',
                        }}
                      >
                        {story.summary}
                      </p>

                      {/* Operational Impact Callout Box */}
                      <div
                        style={{
                          background: 'rgba(255, 255, 255, 0.025)',
                          borderLeft: `3px solid ${story.accentColor}`,
                          borderRadius: '0 8px 8px 0',
                          padding: '0.65rem 0.85rem',
                          marginBottom: '1rem',
                        }}
                      >
                        <div
                          style={{
                            fontSize: '0.6875rem',
                            fontFamily: 'var(--font-mono)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.06em',
                            color: 'var(--text-muted)',
                            marginBottom: '0.2rem',
                          }}
                        >
                          Operational Impact
                        </div>
                        <div
                          style={{
                            fontSize: '0.785rem',
                            color: 'var(--text-primary)',
                            lineHeight: 1.45,
                          }}
                        >
                          {story.impact}
                        </div>
                      </div>
                    </div>

                    {/* Card Bottom: Risk Score + Action Link */}
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        paddingTop: '0.875rem',
                        borderTop: '1px solid var(--border-subtle)',
                        marginTop: 'auto',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            color: 'var(--text-muted)',
                            fontFamily: 'var(--font-mono)',
                            textTransform: 'uppercase',
                          }}
                        >
                          Risk:
                        </span>
                        <span
                          style={{
                            fontSize: '0.85rem',
                            fontFamily: 'var(--font-mono)',
                            fontWeight: 700,
                            color: story.accentColor,
                          }}
                        >
                          {story.riskScore}/100
                        </span>
                      </div>

                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          fontSize: '0.75rem',
                          color: 'var(--text-secondary)',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        <span>INVESTIGATE</span>
                        <ArrowUpRight size={13} />
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>

          {/* Dots Indicator */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '0.5rem',
              marginTop: '2rem',
            }}
          >
            {STORIES.map((_, dotIdx) => {
              const isActive = dotIdx === currentIndex;
              return (
                <button
                  key={dotIdx}
                  onClick={() => {
                    setDirection(dotIdx > currentIndex ? 'next' : 'prev');
                    setCurrentIndex(dotIdx);
                  }}
                  style={{
                    width: isActive ? 24 : 8,
                    height: 8,
                    borderRadius: 4,
                    background: isActive ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.15)',
                    border: 'none',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    padding: 0,
                  }}
                  aria-label={`Jump to incident story ${dotIdx + 1}`}
                />
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
