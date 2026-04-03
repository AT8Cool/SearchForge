import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

type PageItem = number | 'ellipsis';

function buildPageItems(currentPage: number, totalPages: number): PageItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set<number>([1, totalPages, currentPage]);

  for (let page = currentPage - 1; page <= currentPage + 1; page += 1) {
    if (page > 1 && page < totalPages) {
      pages.add(page);
    }
  }

  if (currentPage <= 3) {
    pages.add(2);
    pages.add(3);
    pages.add(4);
  }

  if (currentPage >= totalPages - 2) {
    pages.add(totalPages - 1);
    pages.add(totalPages - 2);
    pages.add(totalPages - 3);
  }

  const sortedPages = Array.from(pages)
    .filter((page) => page >= 1 && page <= totalPages)
    .sort((left, right) => left - right);

  const items: PageItem[] = [];

  sortedPages.forEach((page, index) => {
    if (index > 0 && page - sortedPages[index - 1] > 1) {
      items.push('ellipsis');
    }
    items.push(page);
  });

  return items;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) {
    return null;
  }

  const pageItems = buildPageItems(currentPage, totalPages);

  return (
    <div className="flex w-full flex-wrap items-center justify-center gap-2 py-6 sm:py-8">
      {/* Previous Button */}
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        aria-label="Go to previous page"
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
      <div className="flex max-w-full flex-wrap items-center justify-center gap-1">
        {pageItems.map((item, index) => {
          if (item === 'ellipsis') {
            return (
              <span
                key={`ellipsis-${index}`}
                className="px-2 py-2 text-[14px] text-muted-foreground"
              >
                ...
              </span>
            );
          }

          return (
            <button
              key={item}
              onClick={() => onPageChange(item)}
              aria-label={`Go to page ${item}`}
              aria-current={currentPage === item ? 'page' : undefined}
              className={`
                px-3 py-2 rounded-lg text-[14px] min-w-[40px]
                transition-all duration-200
                ${currentPage === item
                  ? 'bg-blue-600 dark:bg-blue-500 text-white scale-105'
                  : 'text-foreground hover:bg-secondary hover:scale-105'
                }
              `}
            >
              {item}
            </button>
          );
        })}
      </div>

      {/* Next Button */}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        aria-label="Go to next page"
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
