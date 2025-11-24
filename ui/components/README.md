# ui/components

Shared React/Tailwind components for ZULU.

## Components

- `Hero.tsx`: Landing page hero with animated headline
- `Features.tsx`: Feature showcase grid
- `TwoAgents.tsx`: 2-agent architecture visualization
- `CallToAction.tsx`: Download CTA section

## Design System

- **Tailwind CSS**: Utility-first styling
- **Dark theme**: Zinc palette
- **Framer Motion**: Smooth animations
- **Accessibility**: ARIA labels, keyboard navigation

## Usage

```tsx
import { Hero, Features, TwoAgents, CallToAction } from '@/components';

export default function Page() {
  return (
    <>
      <Hero />
      <Features />
      <TwoAgents />
      <CallToAction />
    </>
  );
}
```

See `ui/nextjs/` for full Next.js implementation.
