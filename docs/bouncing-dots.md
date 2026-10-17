# BouncingDots integration

The project uses React, Vite and TypeScript. Global styles live in `src/style.css`, banking styles in `src/bank.css` and `src/bank-theme.css`. Tailwind and shadcn CLI configuration are not installed.

Reusable UI components now live in `src/components/ui/`: this is the source-root equivalent of `/components/ui`, keeps reusable controls together and matches shadcn's conventional `@/components/ui` import path. `bouncing-dots.tsx` is used by the banking analysis loading state in `src/main.tsx`. `demo.tsx` exports an isolated preview, without registering an application route.

The supplied motion timing, dot dimensions, offset and bounce are preserved. Plain CSS replaces the supplied Tailwind classes, using banking palette variables. No images, additional providers or application state are required. `useReducedMotion` stops the bounce when the operating system requests reduced motion. The parent provides the localized loading status; the dots are decorative.

## Optional Tailwind and shadcn setup

The integrated loader works without these steps. To enable Tailwind and the shadcn CLI for future components:

1. Run `npm install tailwindcss @tailwindcss/vite`.
2. Import `tailwindcss` from `@tailwindcss/vite` in `vite.config.ts` and add `tailwindcss()` to its existing plugins array alongside `react()`.
3. Create a CSS entry importing `tailwindcss`, and import it from `src/main.tsx`. Review Tailwind's base styles against both existing visual themes before adopting the entry globally.
4. Add `"baseUrl": "."` and `"paths": {"@/*": ["./src/*"]}` to `tsconfig.json` compilerOptions. Add the matching Vite resolve alias, e.g. `resolve: {alias: {'@': new URL('./src', import.meta.url).pathname}}` with a Windows-safe `fileURLToPath` from `node:url` instead of `.pathname` on Windows.
5. Run `npx shadcn@latest init`, select the Vite project, and configure the UI alias as `@/components/ui`. Review generated global CSS so the bank palette stays scoped to `.bank-mode` and the Minecraft theme retains its own styles.

TypeScript is already configured; no additional setup is needed.

Official guides: https://tailwindcss.com/docs/installation/using-vite and https://ui.shadcn.com/docs/installation/vite.
