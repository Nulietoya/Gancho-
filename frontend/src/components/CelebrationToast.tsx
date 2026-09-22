import { useEffect } from "react";
import { useCelebrationStore } from "../store/celebrationStore";

export function CelebrationToast() {
  const message = useCelebrationStore((s) => s.message);
  const detail = useCelebrationStore((s) => s.detail);
  const key = useCelebrationStore((s) => s.key);
  const dismiss = useCelebrationStore((s) => s.dismiss);

  useEffect(() => {
    if (!message) return;
    const id = setTimeout(dismiss, 3200);
    return () => clearTimeout(id);
  }, [message, key, dismiss]);

  if (!message) return null;

  return (
    <div className="celebration" role="status" key={key} onClick={dismiss}>
      <span className="celebration__burst" aria-hidden="true">
        {Array.from({ length: 8 }, (_, i) => (
          <i key={i} style={{ ["--i" as string]: i }} />
        ))}
      </span>
      <span className="celebration__check" aria-hidden="true">✓</span>
      <span>
        <strong>{message}</strong>
        {detail && <small>{detail}</small>}
      </span>
    </div>
  );
}
