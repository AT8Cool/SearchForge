import { useNavigate } from 'react-router';
import { Header } from '../components/Header';
import { SearchBar } from '../components/SearchBar';
import { Moon, Sun } from 'lucide-react';
import { QuickSuggestion } from '../components/QuickSuggestion';
import { useTheme } from '../context/ThemeContext';

const DEMO_SUGGESTIONS = [
  'Computer Science',
  'What is Database',
  'Python',
  'NASA Moon Mission',
  'Web Development',
  'Cancer',
  'Heart Health',
];

export function Home() {
  const { isDarkMode, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleSearch = (query: string) => {
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query)}`);
    }
  };

  return (
    <div>
      <div className="min-h-screen w-full bg-background relative">
        {/* Theme Toggle Button */}
        <button
          onClick={toggleTheme}
          className="
            fixed top-4 left-4 sm:top-6 sm:left-6 z-50
            p-2.5 sm:p-3 rounded-full
            bg-secondary/80 hover:bg-secondary
            transition-all duration-200
            shadow-[0_2px_8px_rgba(0,0,0,0.08)]
            hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)]
          "
          aria-label="Toggle theme"
        >
          {isDarkMode ? (
            <Sun className="size-4 sm:size-5 text-foreground" />
          ) : (
            <Moon className="size-4 sm:size-5 text-foreground" />
          )}
        </button>

        {/* Page Frame */}
        <div className="max-w-[1440px] mx-auto min-h-screen flex flex-col">
          <Header />

          {/* Hero Section - Centered */}
          <main className="relative z-0 flex-1 flex flex-col items-center justify-center px-4 sm:px-8 md:px-12 -mt-16 sm:-mt-20">
            {/* Logo */}
            <h1 className="text-[48px] sm:text-[60px] md:text-[72px] tracking-[0.08em] text-foreground select-none">
              Vichar
            </h1>

            {/* Tagline */}
            <p className="text-[15px] sm:text-[17px] md:text-[18px] tracking-[0.02em] text-[#6B7280] dark:text-[#9CA3AF] mt-2 sm:mt-3 text-center">
              Search, the thoughtful way.
            </p>

            {/* Search Bar */}
            <div className="mt-8 sm:mt-10 md:mt-12 w-full max-w-[90vw] sm:max-w-[600px] md:max-w-[680px]">
              <SearchBar onSearch={handleSearch} />
            </div>

            <div className="mt-6 flex w-full max-w-[90vw] sm:max-w-[600px] md:max-w-[760px] flex-col items-center gap-3">
              <p className="text-center text-[13px] uppercase tracking-[0.24em] text-muted-foreground/80">
                Try these searches
              </p>
              <div className="flex flex-wrap items-center justify-center gap-2.5">
                {DEMO_SUGGESTIONS.map((suggestion) => (
                  <QuickSuggestion
                    key={suggestion}
                    label={suggestion}
                    onClick={() => handleSearch(suggestion)}
                  />
                ))}
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
