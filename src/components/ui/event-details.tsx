import type {ReactNode} from 'react';

type EventDetailsProps = {
  open: boolean;
  animated: boolean;
  children: ReactNode;
};

export function EventDetails({open, animated, children}: EventDetailsProps) {
  // Preserve the original conditional rendering in the game interface.
  if (!animated) return open ? <>{children}</> : null;
  return (
    <div className={`event-details ${open ? 'is-open' : ''}`} inert={!open} aria-hidden={!open}>
      <div className="event-details-inner">{children}</div>
    </div>
  );
}
