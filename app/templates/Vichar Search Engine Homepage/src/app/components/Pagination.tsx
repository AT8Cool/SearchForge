import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const pages = Array.from({ length: totalPages }, (_, i) => i + 1);
  
  return (
    <div className="flex flex-wrap items-center justify-center gap-2 py-6 sm:py-8">
      {/* Previous Button */}
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className={`
          flex items-center gap-1 px-3 py-2 rounded-lg text-[14px]
          transition-all
          ${currentPage === 1
            ? 'text-muted-foreground/40 cursor-not-allowed'
            : 'text-blue-600 dark:text-blue-400 hover:bg-secondary'
          }
        `}
      >
        <ChevronLeft className="size-4" />
        <span className="hidden sm:inline">Previous</span>
      </button>

      {/* Page Numbers */}
      <div className="flex items-center gap-1">
        {pages.map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={`
              px-3 py-2 rounded-lg text-[14px] min-w-[40px]
              transition-all duration-200
              ${currentPage === page
                ? 'bg-blue-600 dark:bg-blue-500 text-white scale-105'
                : 'text-foreground hover:bg-secondary hover:scale-105'
              }
            `}
          >
            {page}
          </button>
        ))}
      </div>

      {/* Next Button */}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className={`
          flex items-center gap-1 px-3 py-2 rounded-lg text-[14px]
          transition-all
          ${currentPage === totalPages
            ? 'text-muted-foreground/40 cursor-not-allowed'
            : 'text-blue-600 dark:text-blue-400 hover:bg-secondary'
          }
        `}
      >
        <span className="hidden sm:inline">Next</span>
        <ChevronRight className="size-4" />
      </button>
    </div>
  );
}
