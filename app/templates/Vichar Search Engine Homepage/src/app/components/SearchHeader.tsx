import { Search, Moon, Sun } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router';

interface SearchHeaderProps {
  initialQuery?: string;
  isDarkMode?: boolean;
  onToggleTheme?: () => void;
}

export function SearchHeader({ initialQuery = '', isDarkMode = false, onToggleTheme }: SearchHeaderProps) {
  const [query, setQuery] = useState(initialQuery);
  const [isFocused, setIsFocused] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query)}`);
    }
  };

  return (
    <header className="sticky top-0 bg-background border-b border-border/60 z-40">
      <div className="px-4 sm:px-6 md:px-12 py-3 sm:py-4">
        <div className="flex items-center gap-4 sm:gap-6">
          {/* Logo */}
          <a 
            href="/" 
            className="text-[24px] tracking-[0.08em] text-foreground hover:opacity-80 transition-opacity"
          >
            Vichar
          </a>

          {/* Search Bar */}
          <form onSubmit={handleSubmit} className="flex-1 max-w-[600px] lg:max-w-[640px] min-w-0 overflow-hidden
                                                        ml-6 sm:ml-10 lg:ml-20">
            <div 
              className={`
                relative h-[44px] w-full
                bg-background border border-border/40
                rounded-[22px] 
                transition-all duration-200
                overflow-hidden
                ${isFocused 
                  ? 'shadow-[0_0_0_2px_rgba(59,130,246,0.15)] border-blue-400/50' 
                  : 'shadow-[0_1px_4px_rgba(0,0,0,0.06)] hover:shadow-[0_2px_8px_rgba(0,0,0,0.1)]'
                }
              `}
            >
              <div className="flex items-center h-full px-4 gap-3 sm:px-5 gap-2 sm:gap-3">
                <Search className="size-4 text-muted-foreground shrink-0" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setIsFocused(false)}
                  aria-label='Search'
                  placeholder='Vichara?'
                  className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground/60 text-[14px] pl-1 sm:pl-2"
                />
              </div>
            </div>
          </form>

          {/* Navigation */}
          <nav className="flex items-center gap-4 sm:gap-6 ml-auto shrink-0">
            <a 
              href="#about" 
              className="hidden sm:inline text-[14px] text-foreground/70 hover:text-foreground transition-colors"
            >
              About
            </a>
            
            {/* Theme Toggle */}
            {onToggleTheme && (
              <button
                onClick={onToggleTheme}
                className="
                  p-2 rounded-full
                  hover:bg-secondary
                  transition-all duration-200
                "
                aria-label="Toggle theme"
              >
                {isDarkMode ? (
                  <Sun className="size-4 text-foreground" />
                ) : (
                  <Moon className="size-4 text-foreground" />
                )}
              </button>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}