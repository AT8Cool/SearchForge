import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';
import { SearchHeader } from '../components/SearchHeader';
import { ResultCard } from '../components/ResultCard';
import { Pagination } from '../components/Pagination';
import { SkeletonCard } from '../components/SkeletonCard';
import { useTheme } from '../context/ThemeContext';
import { buildApiUrl } from '../lib/api';

export function SearchResults() {
  const [searchParams] = useSearchParams();
  const { isDarkMode, toggleTheme } = useTheme();
  const [currentPage, setCurrentPage] = useState(1);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');

  const query = searchParams.get('q') || '';

  useEffect(() => {
    setCurrentPage(1);
  }, [query]);

  useEffect(() => {
    if (!query) {
      setResults([]);
      setTotal(0);
      setError('');
      return;
    }

    const controller = new AbortController();
    setLoading(true);
    setError('');

    fetch(
      buildApiUrl('/api/search', {
        q: query,
        page: currentPage,
      }),
      { signal: controller.signal }
    )
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`Search request failed with status ${res.status}`);
        }

        return res.json();
      })
      .then((data) => {
        setResults(data.results || []);
        setTotal(data.total || 0);
      })
      .catch((err) => {
        if (err.name === 'AbortError') {
          return;
        }

        console.error(err);
        setResults([]);
        setTotal(0);
        setError('Search is temporarily unavailable. Please try again in a moment.');
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [query, currentPage]);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [currentPage]);

  return (
    <div className="min-h-screen w-full bg-background flex flex-col">
      <SearchHeader
        initialQuery={query}
        isDarkMode={isDarkMode}
        onToggleTheme={toggleTheme}
      />

      <div className="flex-1 px-4 sm:px-6 md:px-12">
        <div className="max-w-[760px] lg:max-w-[820px] w-full mx-auto pt-4 sm:pt-6">
          {loading && (
            <div className="divide-y divide-border/20">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )}

          {!loading && error && (
            <div className="py-16 text-center">
              <p className="text-lg text-foreground">Search is temporarily unavailable</p>
              <p className="text-sm text-muted-foreground mt-2">{error}</p>
            </div>
          )}

          {!loading && !error && results.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-lg text-muted-foreground">
                No results found for "{query}"
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                Try different keywords or simplify your query.
              </p>
            </div>
          )}

          {!loading && !error && results.length > 0 && (
            <div className="py-4 text-[13px] text-muted-foreground">
              Results for "{query}" ({total.toLocaleString()} results)
            </div>
          )}

          {!loading && !error && (
            <div className="divide-y divide-border/20">
              {results.map((result: any, i) => (
                <ResultCard
                  key={i}
                  title={result.title}
                  url={result.url}
                  description={result.snippet}
                />
              ))}
            </div>
          )}

          {!loading && !error && results.length > 0 && (
            <Pagination
              currentPage={currentPage}
              totalPages={Math.ceil(total / 10)}
              onPageChange={setCurrentPage}
            />
          )}
        </div>
      </div>
    </div>
  );
}
