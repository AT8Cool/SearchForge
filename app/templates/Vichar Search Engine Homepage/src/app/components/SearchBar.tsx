import { Search } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface SearchBarProps {
  onSearch?: (query: string) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && query.trim()) {
      onSearch(query);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;

      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') {
        return;
      }

      if (e.key === '/') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <form onSubmit={handleSubmit}>
      <div
        className={`
          relative h-[56px] w-full
          rounded-[28px] border border-border/40 bg-background
          transition-all duration-300 ease-out
          ${isFocused
            ? 'border-blue-400/50 shadow-[0_0_0_3px_rgba(59,130,246,0.15)]'
            : 'shadow-[0_2px_8px_rgba(0,0,0,0.08)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)]'
          }
        `}
      >
        <div className="flex h-full items-center gap-4 px-6">
          <button
            type="submit"
            aria-label="Search"
            className="shrink-0 text-muted-foreground transition-colors hover:text-foreground"
          >
            <Search className="size-5" />
          </button>
          <input
            autoFocus
            ref={inputRef}
            type="text"
            placeholder="Search anything..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            className="flex-1 border-none bg-transparent text-foreground outline-none placeholder:text-muted-foreground/60"
          />
        </div>
      </div>
    </form>
  );
}
