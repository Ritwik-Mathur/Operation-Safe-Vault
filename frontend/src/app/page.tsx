import { Navbar } from "@/components/Navbar";
import { HeroSection } from "@/components/HeroSection";
import { CrisisSection } from "@/components/CrisisSection";
import { OneShieldSolution } from "@/components/OneShieldSolution";
import { FeatureGrid } from "@/components/FeatureGrid";
import { Architecture } from "@/components/Architecture";
import { TeamSection, Footer } from "@/components/Footer";
import { ThreatSandbox } from "@/components/ThreatSandbox";
import { LiveAuditLog } from "@/components/LiveAuditLog";

export default function Home() {
  return (
    <main className="min-h-screen relative">
      {/* Universal Background Texture */}
      <div className="fixed inset-0 noise-overlay z-50 pointer-events-none" />
      
      <Navbar />
      
      <div className="relative">
        <HeroSection />
      </div>

      <div className="relative z-10 py-12 bg-background border-y border-outline/5">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col items-center gap-4 mb-8 text-center">
            <h2 className="text-primary font-headline font-bold uppercase tracking-[0.3em] text-[10px]">Registry Stream</h2>
            <p className="text-on-surface-variant text-sm font-light">Real-time monitoring of global threat neutralizations.</p>
          </div>
          <LiveAuditLog />
        </div>
      </div>
      
      <div id="impact" className="relative z-10">
        <CrisisSection />
      </div>

      <div id="sandbox" className="relative z-10">
        <ThreatSandbox />
      </div>

      <div id="product" className="relative z-10">
        <OneShieldSolution />
        <FeatureGrid />
      </div>

      <div id="tech-stack" className="relative z-10">
        <Architecture />
      </div>

      <div className="relative z-10">
        <TeamSection />
        <Footer />
      </div>
    </main>
  );
}
