import { ArrowLeft, ExternalLink, Github, Linkedin, Moon, Sun } from 'lucide-react';
import { Link } from 'react-router';
import { useTheme } from '../context/ThemeContext';

const PROFILE_LINKS = [
  {
    label: 'GitHub',
    href: 'https://github.com/AT8Cool',
    title: '@AT8Cool',
    description: 'Interested in contributing? Review the source and follow development on GitHub.',
    Icon: Github,
  },
  {
    label: 'LinkedIn',
    href: 'https://www.linkedin.com/in/atharva-bhosale-ab9659302/',
    title: 'Atharva Bhosale',
    description: 'Professional profile, background, and contact information.',
    Icon: Linkedin,
  },
];

export function About() {
  const { isDarkMode, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen w-full bg-background">
      <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-4 sm:px-8 md:px-12">
        <header className="flex items-center justify-between py-5 sm:py-6">
          <Link
            to="/"
            className="inline-flex items-center gap-2 text-[14px] text-foreground/70 transition-colors hover:text-foreground"
          >
            <ArrowLeft className="size-4" />
            Back to search
          </Link>

          <button
            onClick={toggleTheme}
            className="rounded-full p-2 transition-colors hover:bg-secondary"
            aria-label="Toggle theme"
          >
            {isDarkMode ? (
              <Sun className="size-4 text-foreground" />
            ) : (
              <Moon className="size-4 text-foreground" />
            )}
          </button>
        </header>

        <main className="flex flex-1 items-center py-10 sm:py-14">
          <section className="grid w-full gap-8 lg:grid-cols-[1.15fr_0.85fr] lg:gap-10">
            <div className="rounded-[28px] border border-border/50 bg-secondary/20 p-8 sm:p-10">
              <p className="text-[13px] uppercase tracking-[0.28em] text-muted-foreground">
                About Vichar
              </p>
              <h1 className="mt-4 text-[34px] leading-tight text-foreground sm:text-[46px]">
                A search engine prototype designed for technical demonstration.
              </h1>
              <p className="mt-5 max-w-[58ch] text-[15px] leading-8 text-muted-foreground sm:text-[16px]">
                A focused search engine prototype that crawls, indexes, and ranks
                web content using BM25 and PageRank, delivered through a FastAPI
                backend and modern React interface. Built to demonstrate end-to-end
                information retrieval systems in practice.
              </p>
            </div>

            <div className="space-y-4">
              {PROFILE_LINKS.map(({ label, href, title, description, Icon }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  className="group flex items-center justify-between rounded-[24px] border border-border/50 bg-background px-6 py-5 transition-all duration-200 hover:-translate-y-0.5 hover:bg-secondary/35"
                >
                  <div className="flex items-center gap-4">
                    <div className="rounded-2xl bg-secondary p-3 text-foreground">
                      <Icon className="size-5" />
                    </div>
                    <div>
                      <p className="text-[17px] text-foreground">{label}</p>
                      <p className="mt-1 text-[14px] text-foreground/85">{title}</p>
                      <p className="mt-1 max-w-[30ch] text-[13px] leading-6 text-muted-foreground">
                        {description}
                      </p>
                    </div>
                  </div>
                  <ExternalLink className="size-4 text-muted-foreground transition-colors group-hover:text-foreground" />
                </a>
              ))}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
