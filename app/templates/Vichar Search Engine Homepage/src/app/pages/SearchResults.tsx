import { useEffect,useState } from 'react';
import { useSearchParams } from 'react-router';
import { SearchHeader } from '../components/SearchHeader';
import { FilterTabs } from '../components/FilterTabs';
import { ResultCard } from '../components/ResultCard';
import { Pagination } from '../components/Pagination';




export function SearchResults() {
  const [searchParams] = useSearchParams();
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);

  const query = searchParams.get('q') || '';

  useEffect(() =>{
  if (!query) return;

  setLoading(true);

  fetch(`http://127.0.0.1:8000/search?q=${encodeURIComponent(query)}&page = ${currentPage}`)
  .then( res => res.json())
  .then(data => {setResults(data.results || []);
                    setTotal(data.total ||0);
  })
  .catch(err => console.error(err))
  .finally(() => setLoading(false));
  },[query, currentPage]);
  
 

  return (
    <div className={isDarkMode ? 'dark' : ''}>
      <div className="min-h-screen w-full bg-background">
        {/* Search Header */}
        <SearchHeader 
          initialQuery={query} 
          isDarkMode={isDarkMode}
          onToggleTheme={() => setIsDarkMode(!isDarkMode)}
        />

        {/* Main Content */}
        <div className="max-w-[1440px] mx-auto px-12">
          <div className="max-w-[800px] pt-6">
            {/* Filter Tabs */}
            <FilterTabs />

            {loading && <div className="py-4">Loading...</div>}
           
            {/* Results Count */}
            <div className="py-4 text-[13px] text-muted-foreground">
              Results for "{query}" ({results.length} results)
            </div>

            {/* Results List */}
            <div className="divide-y divide-border/20">
              {results.map((result: any, i) => (
                <ResultCard
                  key={i}
                  title={result.title}
                  url={result.url}
                  description={"Score: " + result.score}
                />
              ))}
            </div>

            {/* Pagination */}
            <Pagination 
              currentPage={currentPage}
              totalPages={Math.ceil(total/10)}
              onPageChange={setCurrentPage}
            />
          </div>
        </div>
      </div>
    </div>
  );
}