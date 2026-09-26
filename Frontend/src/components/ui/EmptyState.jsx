import './EmptyState.css';

// The one look for "nothing here" and "couldn't load" panels: what happened, then what to do next.
// `tone="error"` also announces the message to screen readers.
export default function EmptyState({ icon, title, children, actions, tone = 'empty' }) {
  return (
    <div className={`empty-state empty-state--${tone}`} role={tone === 'error' ? 'alert' : undefined}>
      <span className="empty-state-icon" aria-hidden="true">{icon ?? (tone === 'error' ? '⚠️' : '🦎')}</span>
      {title && <p className="empty-state-title">{title}</p>}
      {children && <p className="empty-state-text">{children}</p>}
      {actions && <div className="empty-state-actions">{actions}</div>}
    </div>
  );
}
