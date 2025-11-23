export default function CallToAction() {
  return (
    <section
      id="download"
      className="py-20 border-t border-zinc-800/80 flex flex-col md:flex-row md:items-center md:justify-between gap-8"
    >
      <div>
        <h2 className="text-2xl md:text-3xl font-semibold mb-2">
          Be your own AI department.
        </h2>
        <p className="text-sm text-zinc-400 max-w-xl">
          Install ZULU, run Whisper + your LLM locally, and let a private agent
          handle recall, follow-ups, and evidence — while your data never leaves
          your hardware.
        </p>
      </div>
      <div className="flex flex-col sm:flex-row gap-3">
        <button className="px-6 py-3 rounded-xl bg-emerald-500 text-black font-semibold hover:bg-emerald-400 transition">
          Download desktop build
        </button>
        <a
          href="https://github.com/edgeconsultinglabs/zulu.cash"
          className="px-6 py-3 rounded-xl border border-zinc-700 text-zinc-200 hover:bg-zinc-900/60 transition text-center"
        >
          View source on GitHub
        </a>
      </div>
    </section>
  );
}
