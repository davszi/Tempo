export function TempoLogo({ className = "" }: { className?: string }) {
  return (
    <div className={`tempo-logo ${className}`} aria-label="TEMPO Chess Learning">
      <span className="tempo-logo-mark" aria-hidden="true">
        ♞
      </span>
      <span className="tempo-logo-copy">
        <b>TEMPO</b>
        <small>CHESS LEARNING</small>
      </span>
    </div>
  );
}
