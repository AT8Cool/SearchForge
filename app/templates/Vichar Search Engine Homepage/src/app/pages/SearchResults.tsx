import { useEffect,useState } from 'react';
import { useSearchParams } from 'react-router';
import { SearchHeader } from '../components/SearchHeader';
import { FilterTabs } from '../components/FilterTabs';
import { ResultCard } from '../components/ResultCard';
import { Pagination } from '../components/Pagination';
import { SkeletonCard } from '../components/SkeletonCard';
import { useTheme } from '../context/ThemeContext';


export function SearchResults() {
  const [searchParams] = useSearchParams();
  const { isDarkMode, toggleTheme } = useTheme();
  const [currentPage, setCurrentPage] = useState(1);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const query = searchParams.get('q') || '';

  useEffect(() =>{
  if (!query) return;

  setLoading(true);

  fetch(`http://127.0.0.1:8000/search?q=${encodeURIComponent(query)}&page=${currentPage}`)
  .then( res => res.json())
  .then(data => {setResults(data.results || []);
                    setTotal(data.total ||0);
  })
  .catch(err => console.error(err))
  .finally(() => setLoading(false));
  },[query, currentPage]);
  
  useEffect(() => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
}, [currentPage]);
 


  return (
    <div>
      <div className="min-h-screen w-full bg-background flex flex-col">
        {/* Search Header */}
        <SearchHeader 
          initialQuery={query} 
          isDarkMode={isDarkMode}
          onToggleTheme={toggleTheme}
        />

        {/* Main Content <div className="max-w-[1440px] mx-auto px-12"> <div className="max-w-[800px] pt-6">*/}
        <div className="flex-1 px-4 sm:px-6 md:px-12">
          <div className="max-w-[760px] lg:max-w-[820px] w-full mx-auto pt-4 sm:pt-6">
            {/* Filter Tabs */}
            {/* <FilterTabs /> */}

            {/* Loading State */}
            {loading && (
              <div className="divide-y divide-border/20">
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonCard key={i} />
                ))}
              </div>
            )}

          {!loading && results.length === 0 && (
            <div className="py-16 text-center">
              <p className="text-lg text-muted-foreground">
                No results found for "{query}"
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                Try different keywords or simplify your query.
              </p>
            </div>
          )}
            
           
            {/* Results Count */}
            {!loading && results.length > 0 && (
              <div className="py-4 text-[13px] text-muted-foreground">
                Results for "{query}" ({total.toLocaleString()} results)
              </div>
            )}

            {/* Results List */}
            {!loading && (
            <div className="divide-y divide-border/20">
              {results.map((result: any, i) => (
                <ResultCard
                  key={i}
                  title={result.title}
                  url={result.url}
                  description={ result.snippet}
                />
              ))}
            </div>
            )}

            {/* Pagination */}
           {!loading && results.length > 0 && (
              <Pagination 
                currentPage={currentPage}
                totalPages={Math.ceil(total/10)}
                onPageChange={setCurrentPage}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}