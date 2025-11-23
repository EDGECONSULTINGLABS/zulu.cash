const features = [
  {
    title: "Live call companion",
    body: "Join calls, capture key points, decisions and action items in real time – completely local.",
  },
  {
    title: "Private memory graph",
    body: "Every note, summary and follow-up is stored in an encrypted vault that only you control.",
  },
  {
    title: "Zcash-aligned privacy",
    body: "Inspired by shielded ZEC: selective disclosure only, no default surveillance or identity graphs.",
  },
];

export default function Features() {
  return (
    <section className="py-12 border-t border-zinc-800/80">
      <div className="grid md:grid-cols-3 gap-8">
        {features.map((f) => (
          <div
            key={f.title}
            className="rounded-2xl border border-zinc-800 bg-zinc-950/40 p-6"
          >
            <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
            <p className="text-sm text-zinc-400">{f.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
