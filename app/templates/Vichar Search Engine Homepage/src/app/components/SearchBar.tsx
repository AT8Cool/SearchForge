import { Search } from 'lucide-react';
import { useState,useEffect, useRef } from 'react';

interface SearchBarProps {
  onSearch?: (query: string) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch && query.trim()) {
      onSearch(query);
    }
  };

  const inputRef = useRef<HTMLInputElement>(null);
  
 useEffect(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement;

    // ignore if user is already typing in input
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

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
          bg-background border border-border/40
          rounded-[28px] 
          transition-all duration-300 ease-out
          ${isFocused 
            ? 'shadow-[0_0_0_3px_rgba(59,130,246,0.15)] border-blue-400/50' 
            : 'shadow-[0_2px_8px_rgba(0,0,0,0.08)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.12)]'
          }
        `}
        
      >
        <div className="flex items-center h-full px-6 gap-4">
          <Search className="size-5 text-muted-foreground flex-shrink-0" />
          <input autoFocus
            ref ={inputRef}
            type="text"
            placeholder="Search anything…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground/60"
          />
        </div>
      </div>
    </form>
  );
}