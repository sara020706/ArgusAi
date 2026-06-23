import Navbar   from './components/Navbar'
import Footer   from './components/Footer'
import Hero     from './sections/Hero'
import Pipeline from './sections/Pipeline'
import Output   from './sections/Output'
import Signals  from './sections/Signals'
import Install  from './sections/Install'

export default function App() {
  return (
    <>
      <Navbar />
      <Hero />
      <Pipeline />
      <Output />
      <Signals />
      <Install />
      <Footer />
    </>
  )
}
