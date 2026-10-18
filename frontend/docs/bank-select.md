# Banking dropdowns

`src/components/ui/accordion-2.tsx` adapts the supplied BasicDropdown to the existing React/TypeScript application. Its local styles are `src/components/ui/bank-select.css`. A controlled preview is exported by `dropdown-demo.tsx`.

The `Select` adapter accepts the application's existing select props and option children. In bank mode it renders BasicDropdown; in game mode it returns the original native select with its original props. Bank mode is provided by `BankSelectContext` in `src/main.tsx`.

The adapter retains a hidden native select to preserve the existing change handlers and form values. Values, disabled states, translated labels and dynamically added recording options continue to come from application state.

The dropdown uses the existing `framer-motion` dependency (the same motion API as the prompt's `motion/react`) and existing lucide-react icons. No extra package is required. It supports arrow keys, Home/End, Enter/Space, Escape, Tab and typing an option prefix. The selected option has a checkmark. Reduced-motion preferences disable the animation.

The menu is portalled to the banking shell so panels cannot clip it, and positioned relative to its trigger. It opens upwards when necessary, closes on outside interaction, and closes when its surrounding page scrolls.

The project does not use Tailwind or shadcn configuration. CSS equivalents preserve the supplied appearance without changing the game theme. The conventional source-root UI folder is `src/components/ui`; keeping shared controls here also matches shadcn's `@/components/ui` alias convention. Optional Tailwind/shadcn setup instructions are in [bouncing-dots.md](bouncing-dots.md#optional-tailwind-and-shadcn-setup). TypeScript is already installed and configured.
