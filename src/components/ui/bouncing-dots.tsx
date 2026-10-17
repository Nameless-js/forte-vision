import {motion, useReducedMotion} from 'framer-motion';
import './bouncing-dots.css';

export const BouncingDots = () => {
  const reducedMotion = useReducedMotion();
  return (
    <div className="bouncing-dots" aria-hidden="true">
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          className="bouncing-dots__dot"
          style={{left: `${i * 14 + 10}px`}}
          animate={reducedMotion ? {y: 0, scaleY: 1} : {y: [0, -20, 0], scaleY: [0.8, 1.1, 0.8]}}
          transition={reducedMotion ? {duration: 0} : {
            duration: 0.8,
            repeat: Infinity,
            delay: i * 0.1,
            ease: 'easeInOut',
          }}
        />
      ))}
    </div>
  );
};

export default BouncingDots;
