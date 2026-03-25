import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Header } from '../components/Header';
import { SearchBar } from '../components/SearchBar';
import { Moon, Sun } from 'lucide-react';

export function Home() {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const navigate = useNavigate();

  const handleSearch = (query: string) => {
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query)}`);
    }
  };

  return (
    <div className={isDarkMode ? 'dark' : ''}>
      <div className="min-h-screen w-full bg-background relative">
        {/* Theme Toggle Button */}
        <button
          onClick={() => setIsDarkMode(!isDarkMode)}
          className="
            fixed top-6 left-6 z-50
            p-3 rounded-full
            bg-secondary/80 hover:bg-secondary
            transition-all duration-200
            shadow-[0_2px_8px_rgba(0,0,0,0.08)]
            hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)]
          "
          aria-label="Toggle theme"
        >
          {isDarkMode ? (
            <Sun className="size-5 text-foreground" />
          ) : (
            <Moon className="size-5 text-foreground" />
          )}
        </button>

        {/* Light Mode Frame */}
        <div className="max-w-[1440px] mx-auto h-screen flex flex-col">
          <Header />
          
          {/* Hero Section - Centered */}
          <main className="flex-1 flex flex-col items-center justify-center px-12 -mt-20">
            {/* Logo */}
            <h1 className="text-[72px] tracking-[0.08em] text-foreground select-none">
              Vichar
            </h1>
            
            {/* Tagline */}
            <p className="text-[18px] tracking-[0.02em] text-[#6B7280] dark:text-[#9CA3AF] mt-3">
              Search, the thoughtful way.
            </p>

            {/* Search Bar */}
            <div className="mt-12">
              <SearchBar onSearch={handleSearch} />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
