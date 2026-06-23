export default function SectionHeader({ label, title, subtitle, centered = true }) {
  const align = centered ? 'text-center items-center' : 'text-left items-start'
  return (
    <div className={`flex flex-col gap-3 mb-12 ${align}`}>
      {label && (
        <span className="inline-flex self-start bg-argus-50 text-argus-600 text-xs font-semibold rounded-full px-3 py-1 uppercase tracking-wide">
          {label}
        </span>
      )}
      <h2 className="text-3xl md:text-4xl font-bold text-gray-900 leading-tight">{title}</h2>
      {subtitle && (
        <p className="text-lg text-gray-500 max-w-2xl">{subtitle}</p>
      )}
    </div>
  )
}
