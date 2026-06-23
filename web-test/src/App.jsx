import { motion } from 'framer-motion'
import Navbar       from './components/Navbar'
import Footer       from './components/Footer'
import Hero         from './sections/Hero'
import HowItWorks   from './sections/HowItWorks'
import Features     from './sections/Features'
import LiveDemo     from './sections/LiveDemo'
import AlertFeed    from './sections/AlertFeed'
import ThreatMap    from './sections/ThreatMap'
import CallToAction from './sections/CallToAction'

function FadeSection({ children, id }) {
  return (
    <motion.div
      id={id}
      initial={{ opacity: 0, y: 30 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5 }}
    >
      {children}
    </motion.div>
  )
}

export default function App() {
  return (
    <div className="min-h-screen font-sans">
      <Navbar />
      <Hero />
      <FadeSection id="how-it-works">
        <HowItWorks />
      </FadeSection>
      <FadeSection id="features">
        <Features />
      </FadeSection>
      <FadeSection id="demo">
        <LiveDemo />
      </FadeSection>
      <FadeSection>
        <AlertFeed />
      </FadeSection>
      <FadeSection>
        <ThreatMap />
      </FadeSection>
      <FadeSection>
        <CallToAction />
      </FadeSection>
      <Footer />
    </div>
  )
}
