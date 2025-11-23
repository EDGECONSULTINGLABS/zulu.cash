# ZULU UI — Electron + Tailwind

## Overview

ZULU's user interface is built with:
- **Electron** — Cross-platform desktop app
- **Tailwind CSS** — Modern styling
- **React** — Component-based UI
- **shadcn/ui** — Beautiful components

## Directory Structure

```
ui/
├── electron/           # Electron main process
│   ├── main.js
│   ├── preload.js
│   └── package.json
└── tailwind/          # Tailwind config
    ├── tailwind.config.js
    └── styles/
```

## Key Features

### System Tray Integration
- Minimize to tray
- Quick access menu
- Status indicators

### Notification System
- Transcription alerts
- Memory updates
- Call join notifications

### Privacy Indicators
- Local-only badge
- Encryption status
- No cloud icon

## Design Principles

### Privacy-First UI
- Clear indication of local-only processing
- No cloud status indicators
- Encryption badges

### Minimal & Fast
- Clean interface
- Fast startup
- Low memory footprint

### User Control
- Easy pause/resume
- Manual memory deletion
- Receiver management

## Next Steps

- [ ] Implement Electron app
- [ ] Add Tailwind styling
- [ ] Build React components
- [ ] Add system tray integration

---

> **Beautiful UI. Private Data.**
