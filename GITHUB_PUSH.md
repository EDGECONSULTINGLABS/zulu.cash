# 📤 GitHub Push Guide - ZULU Dragon Mode

**Push ZULU to GitHub with all sensitive data hidden.**

---

## Pre-Push Checklist

The enhanced `.gitignore` will automatically hide:
- ✅ All local databases (`*.db`, `*.sqlite`, `*.sqlcipher`)
- ✅ Audio files (`*.wav`, `*.mp3`)
- ✅ Models and binaries (`/models/`, `*.bin`, `*.pt`)
- ✅ Logs and temp files (`/logs/`, `/data/`, `/storage/`)
- ✅ Environment secrets (`.env`, `*_SECRET*`, `*_KEY*`)
- ✅ Development notes (local `.md` files)
- ✅ Wallet data (`/wallet/`, `*.key`, `*.pem`)

---

## Quick Push (3 Commands)

```bash
# 1. Stage all changes
git add .

# 2. Commit with message
git commit -m "🐉 Dragon Mode v1.0 - Live WhisperX Agent Production Ready"

# 3. Push to GitHub
git push origin main
```

**Done!** Your repo is now clean and judge-ready. 🎉

---

## Detailed Steps

### 1. Review What Will Be Committed

```bash
git status
```

**Expected output:**
```
Changes to be committed:
  modified:   .gitignore
  new file:   DEPLOYMENT.md
  new file:   examples/dragon-mode-session.txt
  new file:   agents/zulu-mpc-agent/DRAGON_MODE.md
  modified:   agents/zulu-mpc-agent/agent_core/llm/summarizer.py
  modified:   agents/zulu-mpc-agent/agent_core/llm/ollama_client.py
  modified:   agents/zulu-mpc-agent/live_whisperx_agent.py
```

**Should NOT see:**
- ❌ `/data/` or `/storage/` folders
- ❌ `*.db` or `*.sqlite` files
- ❌ `*.wav` or `*.mp3` files
- ❌ `/models/` folder
- ❌ `.env` files
- ❌ `/wallet/` folder
- ❌ Local development notes (`DEMO_READY.md`, etc.)

### 2. Check for Sensitive Data

```bash
# Search for potential secrets
git diff --cached | grep -i "secret\|password\|token\|key"

# Search for local paths
git diff --cached | grep -i "C:\\\Users"
```

**If you find any:**
```bash
git reset HEAD <file>  # Unstage the file
# Edit to remove sensitive data
git add <file>
```

### 3. Commit Changes

```bash
git add .
git commit -m "🐉 Dragon Mode v1.0 - Production Ready

Features:
- Real-time WhisperX transcription
- Local LLM summarization (Ollama)
- SQLCipher encryption
- MPC integration (Nillion)
- Privacy-first architecture
- Zero cloud dependencies

All sensitive data excluded via .gitignore"
```

### 4. Push to GitHub

```bash
# Push to main branch
git push origin main

# Or if using different branch
git push origin your-branch-name
```

---

## What Gets Pushed

### ✅ Included (Judge-Ready)

**Core Agent:**
- `agents/zulu-mpc-agent/` — Complete Dragon Mode implementation
- `agent_core/` — All processing modules
- `cli.py` — Command-line interface
- `live_whisperx_agent.py` — Main agent orchestrator
- `requirements.txt` — Python dependencies

**Documentation:**
- `README.md` — Main project overview
- `DEPLOYMENT.md` — Setup guide
- `agents/zulu-mpc-agent/DRAGON_MODE.md` — Technical deep-dive
- `examples/dragon-mode-session.txt` — Sample output

**Configuration:**
- `.gitignore` — Enhanced privacy protection
- `.env.template` — Example environment variables
- `LICENSE` — MIT license

### ❌ Excluded (Private/Local)

**Data & Storage:**
- `/data/` — All local databases
- `/storage/` — Encrypted vaults
- `/logs/` — Log files
- `*.db`, `*.sqlite`, `*.sqlcipher` — Database files

**Models & Binaries:**
- `/models/` — Downloaded ML models
- `*.bin`, `*.pt`, `*.pth` — Model weights
- `ffmpeg-8.0.1/` — FFmpeg binaries

**Secrets & Keys:**
- `.env` — Environment variables
- `/wallet/` — Wallet data
- `*.key`, `*.pem` — Private keys
- `*_SECRET*`, `*_KEY*` — Any secret files

**Temporary Files:**
- `*.wav`, `*.mp3`, `*.flac` — Audio recordings
- `/temp/`, `/tmp/` — Temporary directories
- `__pycache__/` — Python cache

**Development Notes:**
- `DEMO_READY.md`
- `DEPLOYMENT_STATUS.md`
- `ISSUE_RESOLVED.md`
- `LAUNCH_SUCCESS.md`
- `LIVE_AGENT_WORKAROUND.md`
- `README_VERIFICATION.md`
- `run_test.bat`
- `test_*.py` — Test scripts

---

## Verify Clean Push

After pushing, visit your GitHub repo and verify:

1. **No sensitive data visible**
   - Check for personal paths (C:\Users\...)
   - Check for secret keys or tokens
   - Check for `.db` files

2. **Documentation complete**
   - README.md looks professional
   - DEPLOYMENT.md has clear instructions
   - DRAGON_MODE.md explains the tech

3. **Example output clean**
   - No personal file paths
   - Generic placeholders used

4. **Code is functional**
   - All imports present
   - No broken references
   - Ready to clone and run

---

## Post-Push Actions

### 1. Create GitHub Release (Optional)

```bash
git tag -a v1.0-dragon-mode -m "Dragon Mode v1.0 - Production Ready"
git push origin v1.0-dragon-mode
```

Then create a release on GitHub:
- Title: **ZULU Dragon Mode v1.0**
- Description: See `DRAGON_MODE.md`
- Assets: None (code only)

### 2. Update README Badges (Optional)

Add status badges to README:
```markdown
![Dragon Mode](https://img.shields.io/badge/Dragon%20Mode-Production-red?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Live-success?style=for-the-badge)
```

### 3. Share with Judges

Your repo is now **judge-ready**! Share the link:
```
https://github.com/edgeconsultinglabs/zulu.cash
```

**Key files for judges:**
1. `README.md` — Project overview
2. `agents/zulu-mpc-agent/DRAGON_MODE.md` — Technical details
3. `DEPLOYMENT.md` — How to run it
4. `examples/dragon-mode-session.txt` — Proof it works

---

## Troubleshooting

### "Still seeing sensitive files"

**Check .gitignore is working:**
```bash
git check-ignore -v data/zulu_agent.db
git check-ignore -v .env
```

**Should output:**
```
.gitignore:60:/data/    data/zulu_agent.db
.gitignore:35:.env      .env
```

**Force remove cached files:**
```bash
git rm -r --cached data/
git rm --cached .env
git commit -m "Remove sensitive data"
```

### "Accidentally pushed secrets"

**IMMEDIATELY:**

1. **Rotate all secrets** (API keys, tokens)
2. **Remove from history:**
   ```bash
   # Using BFG Repo-Cleaner
   bfg --delete-files .env
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push --force
   ```

3. **Verify secrets are gone:**
   ```bash
   git log --all --full-history -- ".env"
   ```

### "File too large"

GitHub has 100MB limit per file.

**For large models:**
- Add to `.gitignore`
- Use Git LFS (not recommended for this project)
- Document where to download in README

---

## Best Practices

1. **Always review before pushing:**
   ```bash
   git diff --cached
   ```

2. **Use descriptive commit messages:**
   ```bash
   git commit -m "feat: Add Dragon Mode live recording UI"
   git commit -m "fix: Resolve LLM JSON parsing error"
   git commit -m "docs: Update deployment guide"
   ```

3. **Keep development notes local:**
   - Personal TODO lists
   - Internal discussions
   - Test outputs
   - All covered by `.gitignore`

4. **Never commit:**
   - API keys or tokens
   - Database files
   - Audio recordings
   - Personal information
   - Absolute file paths

---

## Final Checklist Before Push

- [ ] Reviewed `git status` output
- [ ] No `.db` or `.sqlite` files staged
- [ ] No `.env` files staged
- [ ] No audio files (`.wav`, `.mp3`) staged
- [ ] No `/data/` or `/storage/` folders staged
- [ ] No personal file paths in code
- [ ] Documentation complete and clean
- [ ] Example output redacted
- [ ] License file present
- [ ] README is professional

**All checked?** You're ready to push! 🚀

```bash
git push origin main
```

---

**🐉 ZULU Dragon Mode is going live. Judge-ready. Privacy-preserved. Let's go. 🐉**
