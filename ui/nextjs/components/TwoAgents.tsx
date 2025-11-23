export default function TwoAgents() {
  return (
    <section className="py-16 border-t border-zinc-800/80">
      <div className="mb-8">
        <h2 className="text-3xl font-semibold mb-3">
          Two agents. One warrior. Zero correlation.
        </h2>
        <p className="text-zinc-400 max-w-2xl">
          ZULU splits cognition and value so your conversations and your coins
          never sit in the same blast radius.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Live agent */}
        <div className="rounded-2xl border border-zinc-800 bg-gradient-to-br from-zinc-950 via-zinc-900 to-zinc-950 p-6">
          <h3 className="text-xl font-semibold mb-2">Zulu Live — Call Agent</h3>
          <p className="text-sm text-zinc-400 mb-4">
            Handles audio, context and personal memory. Joins your calls,
            transcribes locally with Whisper, and uses a local LLM to build a
            private knowledge base just for you.
          </p>
          <ul className="text-sm text-zinc-300 space-y-1">
            <li>• No wallet access</li>
            <li>• No transaction data</li>
            <li>• Encrypted <code>memory.db</code> (SQLCipher)</li>
          </ul>
        </div>

        {/* Ledger agent */}
        <div className="rounded-2xl border border-emerald-500/40 bg-gradient-to-br from-zinc-950 via-emerald-950/40 to-zinc-950 p-6">
          <h3 className="text-xl font-semibold mb-2">Zulu Ledger — Value Agent</h3>
          <p className="text-sm text-zinc-400 mb-4">
            Separately, a ledger agent can scan view-only keys, classify ZEC
            flows, and export evidence for taxes or reporting — without ever
            seeing your conversations.
          </p>
          <ul className="text-sm text-zinc-300 space-y-1">
            <li>• View keys only, never spend keys</li>
            <li>• Encrypted <code>ledger.db</code> (SQLCipher)</li>
            <li>• Designed for selective disclosure, not monitoring</li>
          </ul>
        </div>
      </div>
    </section>
  );
}
