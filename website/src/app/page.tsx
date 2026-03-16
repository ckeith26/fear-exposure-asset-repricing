import Navigation from "@/components/Navigation";
import Hero from "@/components/sections/Hero";
import ResearchQuestion from "@/components/sections/ResearchQuestion";
import DataSample from "@/components/sections/DataSample";
import DataSources from "@/components/sections/DataSources";
import Methodology from "@/components/sections/Methodology";
import Results from "@/components/sections/Results";
import Robustness from "@/components/sections/Robustness";
import Limitations from "@/components/sections/Limitations";
import DataDownload from "@/components/sections/DataDownload";
import About from "@/components/sections/About";

export default function Home() {
  return (
    <>
      <Navigation />
      <main className="pt-12">
        <Hero />
        <ResearchQuestion />
        <DataSample />
        <DataSources />
        <Methodology />
        <Results />
        <Robustness />
        <Limitations />
        <DataDownload />
        <About />
      </main>
      <footer
        className="text-center py-8 text-xs"
        style={{ color: "var(--color-text-secondary)", borderTop: "1px solid var(--color-border)" }}
      >
        <p>FEAR - Flood Exposure and Asset Repricing</p>
        <p className="mt-1">
          <a
            href="https://cameronkeithgolf.com"
            target="_blank"
            rel="noopener noreferrer"
            className="underline transition-colors duration-200 hover:text-[var(--color-accent)]"
            style={{ color: "inherit" }}
          >
            Cameron Keith
          </a>
          {" "}&middot; Econ 66 &middot; Dartmouth College
        </p>
      </footer>
    </>
  );
}
