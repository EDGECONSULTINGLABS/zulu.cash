import Hero from "@/components/Hero";
import Features from "@/components/Features";
import TwoAgents from "@/components/TwoAgents";
import CallToAction from "@/components/CallToAction";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-black via-zinc-950 to-black text-zinc-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <Hero />
        <Features />
        <TwoAgents />
        <CallToAction />
      </div>
    </main>
  );
}
