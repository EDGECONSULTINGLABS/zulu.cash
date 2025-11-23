# ZULU Quickstart — Run Locally

## 🎯 Prerequisites

### 1. Install Ollama
```bash
# Windows: Download from https://ollama.com/download
# After installation, pull a model:
ollama pull phi3
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install FFmpeg (for Whisper)
```bash
# Windows (using Chocolatey):
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

---

## 🚀 Quick Test

### Test 1: Whisper → Ollama Pipeline

Create a test audio file or use your own:

```bash
python scripts/zulu_live_pipeline.py path/to/your/audio.wav
```

**What it does:**
1. Transcribes audio with Whisper (offline)
2. Analyzes with Ollama phi3 (local LLM)
3. Returns structured JSON with summary, decisions, actions, tags
4. Saves to `storage/meeting-{filename}.json`

**Example output:**
```json
{
  "created_at": "2024-11-23T23:55:00",
  "audio_path": "recording.wav",
  "transcript": "Full transcript here...",
  "analysis": {
    "summary": "Discussion about Q4 planning...",
    "decisions": ["Approved budget for new hiring"],
    "actions_mine": ["Review candidate profiles by Friday"],
    "actions_others": ["Sarah: Prepare hiring plan"],
    "tags": ["hiring", "Q4", "budget"]
  }
}
```

---

### Test 2: Initialize Encrypted Databases

```bash
# Create storage directory
mkdir storage

# Initialize memory database
sqlite3 storage/memory.db
> PRAGMA key = 'your-strong-passphrase';
> .read storage/schema_memory.sql
> .quit

# Initialize ledger database
sqlite3 storage/ledger.db
> PRAGMA key = 'different-strong-passphrase';
> .read storage/schema_ledger.sql
> .quit
```

---

### Test 3: Database Operations (Node.js)

```bash
cd scripts
npm install better-sqlite3
node db-memory.ts
```

---

## 🎨 Run Next.js UI (Optional)

```bash
cd ui/nextjs

# Create package.json
npm init -y

# Install dependencies
npm install next@14 react react-dom framer-motion
npm install -D tailwindcss postcss autoprefixer @types/react @types/node typescript

# Initialize Tailwind
npx tailwindcss init -p

# Create tsconfig.json
cat > tsconfig.json << EOF
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "ES2020"],
    "jsx": "preserve",
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "allowJs": true,
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
EOF

# Run dev server
npm run dev
```

Visit: `http://localhost:3000`

---

## 📊 What You Get Locally

### ✅ Working Now:
- **Whisper transcription** → Offline audio-to-text
- **Ollama LLM analysis** → Local structured analysis
- **Encrypted SQLCipher databases** → memory.db + ledger.db
- **Next.js UI components** → Landing page with 2-agent showcase

### 🔄 In Development:
- Electron desktop app
- Real-time audio capture
- ZCash lightwalletd integration
- Embedding generation (FAISS)

---

## 🛠️ Troubleshooting

### Ollama not responding
```bash
# Check Ollama is running
ollama list

# Start Ollama server
ollama serve

# Test connection
curl http://localhost:11434/api/tags
```

### Whisper out of memory
Use a smaller model:
```python
# In zulu_live_pipeline.py, change:
model = whisper.load_model("tiny")  # or "base" instead of "small"
```

### SQLCipher not found
```bash
# Windows
pip install pysqlcipher3

# If that fails, use regular SQLite for testing:
pip install sqlite3
```

---

## 🎯 Next Steps

1. **Test the pipeline** with a sample audio file
2. **Initialize databases** with the schemas
3. **Run the UI** to see the landing page
4. **Read the docs** in `docs/` for architecture details

---

> **Everything runs locally. No cloud. No telemetry. Private by default.** 🔒
