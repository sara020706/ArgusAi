export default function Footer() {
  return (
    <footer className="bg-gray-50 border-t border-gray-100">
      <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500">
        <span className="font-semibold text-gray-700">👁️ Argus — MIT License</span>
        <div className="flex items-center gap-6">
          <a href="https://github.com/yourname/argus" target="_blank" rel="noreferrer"
            className="hover:text-argus-500 transition-colors">GitHub</a>
          <a href="https://github.com/yourname/argus/blob/main/docs/architecture.md"
            target="_blank" rel="noreferrer"
            className="hover:text-argus-500 transition-colors">Docs</a>
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
            className="hover:text-argus-500 transition-colors">API Reference</a>
        </div>
        <span>Built with Python + React</span>
      </div>
    </footer>
  )
}
