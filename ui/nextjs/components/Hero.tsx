"use client";

import { motion } from "framer-motion";

export default function Hero() {
  return (
    <section className="py-20 md:py-28">
      <motion.div
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center"
      >
        <p className="text-xs tracking-[0.25em] uppercase text-zinc-400 mb-4">
          ZULU.CASH · PRIVACY NATIVE
        </p>

        <h1 className="text-4xl md:text-6xl font-semibold mb-6">
          Private AI
          <span className="block bg-gradient-to-r from-amber-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            that remembers <span className="italic">you</span>, not the cloud.
          </span>
        </h1>

        <p className="max-w-2xl mx-auto text-lg text-zinc-300 mb-10">
          ZULU is a local-first AI companion that listens on calls, takes notes,
          and builds a private memory vault that never leaves your device.
          Powered by Zcash's privacy ethos.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <a
            href="#download"
            className="px-6 py-3 rounded-xl bg-zinc-50 text-black font-medium shadow-lg shadow-amber-500/20 hover:bg-zinc-200 transition"
          >
            Download prototype
          </a>
          <a
            href="/docs/litepaper"
            className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-200 hover:bg-zinc-900/60 transition"
          >
            Read litepaper
          </a>
        </div>

        <p className="mt-6 text-sm text-zinc-500">
          Local Whisper · Local LLM · Encrypted SQLCipher vaults · No telemetry.
        </p>
      </motion.div>
    </section>
  );
}
