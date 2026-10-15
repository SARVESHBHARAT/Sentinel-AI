import { useRef, useEffect, useState, useCallback, Suspense, lazy } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Shield, BarChart3, Zap, Activity } from 'lucide-react';
import api from '../api/client';
import type { OverviewResponse } from '../api/client';

// Lazy-load the heavy Three.js scene
const HeroScene = lazy(() => import('../components/HeroScene'));

const FADE_UP: any = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.12, duration: 0.65, ease: [0.16, 1, 0.3, 1] },
  }),
};

export default function HomePage() {
  const navigate = useNavigate();
  const mouseRef = useRef<[number, number]>([0, 0]);
  const [reducedMotion] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  );
  const [webglAvailable, setWebglAvailable] = useState(true);
  const [metrics, setMetrics] = useState<OverviewResponse | null>(null);
  const [recentIncidents, setRecentIncidents] = useState<any[]>([]);

  // WebGL availability check
  useEffect(() => {
    try {
      const canvas = document.createElement('canvas');
      const ctx =
        canvas.getContext('webgl2') ?? canvas.getContext('webgl') ?? canvas.getContext('experimental-webgl');
      setWebglAvailable(!!ctx);
    } catch {
      setWebglAvailable(false);
    }
  }, []);

  // Mouse tracking for 3D parallax
  const handleMouseMove = useCallback((e: MouseEvent) => {
    mouseRef.current = [
      (e.clientX / window.innerWidth - 0.5) * 2,
      (e.clientY / window.innerHeight - 0.5) * 2,
    ];
  }, []);

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [handleMouseMove]);

  // Load real metrics from backend
  useEffect(() => {
    api.overview().then(setMetrics).catch(() => {});
    api.incidents.list({ page_size: 4, sort_by: 'created_at', descending: true }).then((r) => setRecentIncidents(r.incidents)).catch(() => {});
  }, []);

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* ── HERO SECTION ── */}
      <section
        style={{
          position: 'relative',
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          background: 'var(--bg-void)',
        }}
      >
        {/* Background canvas */}
        <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
          {(webglAvailable && !reducedMotion) ? (
            <Suspense fallback={<StaticGradientBg />}>
              <HeroScene mouse={mouseRef} reducedMotion={reducedMotion} />
            </Suspense>
          ) : (
            <StaticGradientBg />
          )}
        </div>

        {/* Radial vignette overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background:
              'radial-gradient(ellipse 80% 60% at 50% 50%, transparent 40%, var(--bg-void) 100%)',
            zIndex: 1,
            pointerEvents: 'none',
          }}
        />

        {/* Hero content */}
        <div
          style={{
            position: 'relative',
            zIndex: 2,
            textAlign: 'center',
            padding: '0 2rem',
            maxWidth: '860px',
          }}
        >
          <motion.div
            className="eyebrow"
            style={{ justifyContent: 'center', marginBottom: '1.5rem' }}
            initial="hidden"
            animate="visible"
            custom={0}
            variants={FADE_UP}
          >
            <span style={{ color: 'var(--accent-cyan)' }}>AI INCIDENT GOVERNANCE</span>
          </motion.div>

          <motion.h1
            initial="hidden"
            animate="visible"
            custom={1}
            variants={FADE_UP}
            style={{
              fontSize: 'clamp(2.25rem, 6vw, 4.5rem)',
              fontWeight: 800,
              letterSpacing: '-0.04em',
              lineHeight: 1.05,
              marginBottom: '1.5rem',
              background: 'linear-gradient(135deg, #e8edf5 0%, #8b9ab4 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            Understand AI failures.
            <br />
            Build trust through evidence.
          </motion.h1>

          <motion.p
            initial="hidden"
            animate="visible"
            custom={2}
            variants={FADE_UP}
            style={{
              fontSize: 'clamp(1rem, 2vw, 1.1875rem)',
              color: 'var(--text-secondary)',
              marginBottom: '2.5rem',
              lineHeight: 1.7,
              maxWidth: '600px',
              margin: '0 auto 2.5rem',
            }}
          >
            Report, investigate, and compare AI incidents across models and providers.
            A governance platform built for accountability.
          </motion.p>

          <motion.div
            initial="hidden"
            animate="visible"
            custom={3}
            variants={FADE_UP}
            style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}
          >
            <button
              className="btn btn-primary btn-lg"
              onClick={() => navigate('/dashboard')}
              style={{ gap: '0.625rem' }}
            >
              Open Observatory
              <ArrowRight size={18} />
            </button>
            <button
              className="btn btn-secondary btn-lg"
              onClick={() => navigate('/explorer')}
            >
              Explore Incident Reports
            </button>
          </motion.div>

          {/* Live metrics strip */}
          {metrics && (
            <motion.div
              initial="hidden"
              animate="visible"
              custom={4}
              variants={FADE_UP}
              style={{
                display: 'flex',
                gap: '2rem',
                justifyContent: 'center',
                marginTop: '3.5rem',
                flexWrap: 'wrap',
              }}
            >
              {[
                { label: 'Incidents Recorded', value: metrics.total },
                { label: 'High / Critical', value: metrics.high_critical },
                { label: 'Awaiting Review', value: metrics.awaiting_review },
                { label: 'Open Cases', value: metrics.open_incidents },
              ].map(({ label, value }) => (
                <div key={label} style={{ textAlign: 'center' }}>
                  <div
                    style={{
                      fontSize: 'clamp(1.5rem, 3vw, 2.25rem)',
                      fontWeight: 800,
                      fontFamily: 'var(--font-sans)',
                      color: 'var(--text-primary)',
                      letterSpacing: '-0.03em',
                      lineHeight: 1,
                    }}
                  >
                    {value}
                  </div>
                  <div
                    style={{
                      fontSize: '0.7rem',
                      letterSpacing: '0.14em',
                      textTransform: 'uppercase',
                      color: 'var(--text-muted)',
                      marginTop: '0.375rem',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {label}
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          style={{
            position: 'absolute',
            bottom: '2rem',
            left: '50%',
            transform: 'translateX(-50%)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '0.5rem',
            color: 'var(--text-muted)',
            fontSize: '0.7rem',
            letterSpacing: '0.15em',
            textTransform: 'uppercase',
            fontFamily: 'var(--font-mono)',
            zIndex: 2,
          }}
        >
          <span>Scroll</span>
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ repeat: Infinity, duration: 1.8, ease: 'easeInOut' }}
            style={{ width: 1, height: 28, background: 'var(--border-default)', borderRadius: 1 }}
          />
        </motion.div>
      </section>

      {/* ── FEATURES SECTION ── */}
      <section
        style={{
          background: 'var(--bg-deep)',
          borderTop: '1px solid var(--border-subtle)',
          padding: '5rem 2rem',
        }}
      >
        <div className="container">
          <motion.div
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true }}
            variants={FADE_UP}
            style={{ textAlign: 'center', marginBottom: '3.5rem' }}
          >
            <div className="page-eyebrow" style={{ justifyContent: 'center', marginBottom: '1rem' }}>
              Platform Capabilities
            </div>
            <h2 style={{ letterSpacing: '-0.03em', marginBottom: '1rem' }}>
              Every tool for AI incident governance
            </h2>
            <p style={{ maxWidth: 540, margin: '0 auto', color: 'var(--text-secondary)' }}>
              From initial report to verified finding, every step is audited, every decision recorded.
            </p>
          </motion.div>

          <div className="grid-4">
            {[
              {
                icon: <Shield size={24} />,
                title: 'Incident Lifecycle',
                description:
                  'Submit → Review → Action → Resolve → Close. Full audit trail with immutable event history.',
                color: '#f5f5f5',
              },
              {
                icon: <Zap size={24} />,
                title: 'AI Triage',
                description:
                  'Automated keyword assessment or live OpenAI analysis. Always advisory; human determination required.',
                color: 'var(--accent-cyan)',
              },
              {
                icon: <BarChart3 size={24} />,
                title: 'Model Intelligence',
                description:
                  'Compare providers, models, and versions by incident counts, severity, and verification rates.',
                color: '#d4d4d8',
              },
              {
                icon: <Activity size={24} />,
                title: 'Verification',
                description:
                  'Human-reviewed evidence chains. Verified, Disputed, or Unverified — never AI-auto-verified.',
                color: '#4ade80',
              },
            ].map(({ icon, title, description, color }, i) => (
              <motion.div
                key={title}
                className="card"
                initial="hidden"
                whileInView="visible"
                viewport={{ once: true }}
                custom={i}
                variants={FADE_UP}
              >
                <div
                  style={{
                    width: 44,
                    height: 44,
                    borderRadius: 10,
                    background: `${color}18`,
                    border: `1px solid ${color}30`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color,
                    marginBottom: '1rem',
                  }}
                >
                  {icon}
                </div>
                <h4 style={{ marginBottom: '0.5rem' }}>{title}</h4>
                <p style={{ fontSize: '0.875rem', margin: 0 }}>{description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── RECENT INCIDENTS ── */}
      {recentIncidents.length > 0 && (
        <section
          style={{
            background: 'var(--bg-void)',
            borderTop: '1px solid var(--border-subtle)',
            padding: '5rem 2rem',
          }}
        >
          <div className="container">
            <motion.div
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={FADE_UP}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '2rem',
              }}
            >
              <div>
                <div className="page-eyebrow" style={{ marginBottom: '0.5rem' }}>Live Data</div>
                <h2 style={{ letterSpacing: '-0.03em' }}>Recent Incidents</h2>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => navigate('/explorer')}
                style={{ flexShrink: 0 }}
              >
                View All <ArrowRight size={14} />
              </button>
            </motion.div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {recentIncidents.map((inc, i) => (
                <motion.div
                  key={inc.incident_id}
                  initial="hidden"
                  whileInView="visible"
                  viewport={{ once: true }}
                  custom={i}
                  variants={FADE_UP}
                  className="card"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem',
                    cursor: 'pointer',
                    padding: '0.875rem 1.25rem',
                  }}
                  onClick={() => navigate(`/incidents/${inc.incident_id}`)}
                >
                  <span className="incident-id">{inc.incident_id}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        color: 'var(--text-primary)',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {inc.title}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.15rem' }}>
                      {inc.provider ?? 'Unknown provider'} · {inc.report_date}
                    </div>
                  </div>
                  {inc.is_demo && <span className="demo-label">DEMO</span>}
                  {inc.severity && (
                    <span
                      className={`badge badge-${inc.severity === 'critical' ? 'critical' : inc.severity === 'high' ? 'high' : inc.severity === 'medium' ? 'medium' : 'low'}`}
                    >
                      {inc.severity}
                    </span>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── FOOTER ── */}
      <footer
        style={{
          background: 'var(--bg-void)',
          borderTop: '1px solid var(--border-subtle)',
          padding: '2rem',
          textAlign: 'center',
          marginTop: 'auto',
        }}
      >
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.7rem',
            color: 'var(--text-muted)',
            letterSpacing: '0.1em',
          }}
        >
          SENTINEL AI · AI INCIDENT GOVERNANCE · FOR TRUSTED NETWORK USE ONLY
        </div>
      </footer>
    </div>
  );
}

function StaticGradientBg() {
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `
          radial-gradient(ellipse 60% 50% at 50% 50%, rgba(255,255,255,0.03) 0%, transparent 65%),
          radial-gradient(ellipse 40% 35% at 20% 60%, rgba(56,189,248,0.05) 0%, transparent 55%),
          var(--bg-void)
        `,
      }}
    />
  );
}
