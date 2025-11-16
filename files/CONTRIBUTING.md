# Contributing to ZULU.cash

First off: thank you for your interest in contributing 🙌  
ZULU is intentionally built **in public**, and contributions are welcome from developers, designers, researchers, and privacy advocates.

---

## 1. Ways You Can Help

- Fix bugs or improve code in `backend/` and `frontend/`
- Improve docs (litepaper, build log, README)
- Add tests for ledger, AI integration, or swap logic
- Help design or refine the NEAR-based swap engine
- Explore private compute / MPC integration
- Improve UX for merchants and users

---

## 2. Getting Started

1. **Fork** the repo on GitHub  
2. **Clone** your fork locally  
3. Set up your environment:

```bash
# backend
cd backend
npm install

# frontend
cd frontend
npm install
```

4. Run dev servers:

```bash
# from backend/
npm run dev

# from frontend/
npm run dev
```

---

## 3. Branching & Pull Requests

* Create feature branches from `main`:

```bash
git checkout -b feature/your-feature-name
```

* Keep commits small and focused
* Write clear commit messages
* Open a Pull Request with:
  * A short description of the change
  * Any relevant screenshots or logs
  * Notes on testing performed

---

## 4. Code Style

* Prefer **TypeScript** for new backend/ frontend modules
* Keep functions small and composable
* Add comments for non-obvious logic, especially:
  * Crypto-related flows
  * Swap routing
  * Security-sensitive code

---

## 5. Issues & Feature Requests

* Use [GitHub Issues](../../issues) to:
  * Report bugs
  * Propose new features
  * Ask implementation questions

When filing issues:

* Include reproduction steps (if bug)
* Include context (why you want the feature)
* Tag with relevant labels if you can

---

## 6. Security-Sensitive Contributions

If your contribution touches:

* Key handling
* Encryption
* Swap safety / routing
* Access control

…please highlight this in your PR and refer to [SECURITY.md](SECURITY.md).

Security issues should **not** be reported via public issues.
Email: `team@edgeconsultinglabs.com`.

---

## 7. License

By contributing, you agree that your contributions will be licensed under the same MIT License that governs this project.

---

Thank you for helping build **private AI for private money.**
