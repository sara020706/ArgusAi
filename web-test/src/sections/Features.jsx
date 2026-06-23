import { MessageSquare, TrendingUp, GitMerge, Globe, Database, Code2 } from 'lucide-react'
import { motion } from 'framer-motion'
import SectionHeader from '../components/SectionHeader'

const FEATURES = [
  {
    icon: MessageSquare,
    title: 'Explainable Alerts',
    desc: "Every alert includes a ranked breakdown of contributing factors. No black boxes — your team knows exactly why.",
  },
  {
    icon: TrendingUp,
    title: 'Adaptive Baselines',
    desc: "Argus learns each user's normal behavior using Welford's online algorithm. No batch retraining required.",
  },
  {
    icon: GitMerge,
    title: 'Event Correlation',
    desc: 'Single events are weak signals. Argus detects multi-step attack patterns across a configurable time window.',
  },
  {
    icon: Globe,
    title: 'Threat Intelligence',
    desc: 'Cross-references IPs against AbuseIPDB. Known malicious IPs escalate the risk score automatically.',
  },
  {
    icon: Database,
    title: 'Plug-in Storage',
    desc: 'Bring your own database. Argus defines the interface — your app implements it with Postgres, MongoDB, or anything.',
  },
  {
    icon: Code2,
    title: 'API-First',
    desc: 'Score events via REST API from any language. Python, Node.js, Go — if it speaks HTTP it works with Argus.',
  },
]

export default function Features() {
  return (
    <section id="features" className="bg-gray-50 py-24">
      <div className="max-w-6xl mx-auto px-6">
        <SectionHeader
          label="Features"
          title="Everything a security team needs"
          subtitle="Built in layers so you use only what you need."
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f, i) => {
            const Icon = f.icon
            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: i * 0.07 }}
                className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md
                  transition-shadow p-6 flex flex-col gap-4"
              >
                <div className="w-10 h-10 rounded-xl bg-argus-50 flex items-center justify-center flex-shrink-0">
                  <Icon size={20} className="text-argus-500" />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900 mb-1.5">{f.title}</h3>
                  <p className="text-sm text-gray-500 leading-relaxed">{f.desc}</p>
                </div>
              </motion.div>
            )
          })}
        </div>
      </div>
    </section>
  )
}
