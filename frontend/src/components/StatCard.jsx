export default function StatCard({ title, value, subtitle, variant = 'default' }) {
  return (
    <div className={`stat-card stat-card--${variant}`}>
      <p className="stat-card-title">{title}</p>
      <p className="stat-card-value">{value}</p>
      {subtitle && <p className="stat-card-subtitle">{subtitle}</p>}
    </div>
  );
}
