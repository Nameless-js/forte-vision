import {useLayoutEffect, useRef} from 'react';

const targets = '.status-strip, .section-heading, .feature-grid > article, .workspace-title, .video-panel, .results-panel, .event-replay, .counter-checks, .benchmark-lab, .station-note, footer';

/** Reveal banking content once, when it reaches the viewport. */
export function useBankScrollReveal(enabled: boolean, page: string) {
  const ref = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    const root = ref.current;
    if (!enabled || !root || !('IntersectionObserver' in window)) return;
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (motion.matches) return;
    const pending = new Set<HTMLElement>();
    const show = (element: HTMLElement) => {
      element.classList.remove('bank-reveal-pending');
      observer.unobserve(element);
      pending.delete(element);
    };
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) show(entry.target as HTMLElement);
      });
    }, {threshold: 0, rootMargin: '0px 0px -32px 0px'});
    const register = () => {
      if (motion.matches) return;
      for (const element of pending) {
        if (!root.contains(element)) show(element);
      }
      root.querySelectorAll<HTMLElement>(targets).forEach(element => {
        if (element.dataset.bankReveal === 'ready' || !element.getClientRects().length) return;
        element.dataset.bankReveal = 'ready';
        // Keep the initial viewport and anything already scrolled past readable.
        if (element.getBoundingClientRect().top < window.innerHeight - 32) return;
        element.classList.add('bank-reveal-pending');
        pending.add(element);
        observer.observe(element);
      });
    };
    const focus = (event: FocusEvent) => {
      if (!(event.target instanceof Element)) return;
      const element = event.target.closest<HTMLElement>('.bank-reveal-pending');
      if (element) show(element);
    };
    const reduceMotion = () => {
      if (motion.matches) pending.forEach(show);
    };
    register();
    const mutations = new MutationObserver(register);
    mutations.observe(root, {childList: true, subtree: true, attributes: true, attributeFilter: ['hidden']});
    root.addEventListener('focusin', focus);
    motion.addEventListener('change', reduceMotion);
    return () => {
      mutations.disconnect();
      observer.disconnect();
      root.removeEventListener('focusin', focus);
      motion.removeEventListener('change', reduceMotion);
      pending.forEach(element => element.classList.remove('bank-reveal-pending'));
      root.querySelectorAll<HTMLElement>('[data-bank-reveal]').forEach(element => delete element.dataset.bankReveal);
    };
  }, [enabled, page]);
  return ref;
}
