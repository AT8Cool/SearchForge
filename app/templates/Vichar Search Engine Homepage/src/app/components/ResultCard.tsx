interface ResultCardProps {
  title: string;
  url: string;
  description: string;
}

function getFavicon(url: string) {
  try {
    const domain = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}`;
  } catch {
    return "";
  }
}

export function ResultCard({ title, url, description }: ResultCardProps) {
  const highlightText = (text: string) => {
    const query = window.location.search.split("q=")[1] || "";
    const terms = decodeURIComponent(query).split(" ").filter(Boolean);

    let result = text;

    terms.forEach(term => {
      const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(${escapedTerm})`, "gi");
      result = result.replace(regex, "<mark>$1</mark>");
    });

    return result;
  };

  const favicon = getFavicon(url);

  return (
    <div className="py-5 group">
      {/* URL row */}
      <div className="flex items-center gap-2 mb-1 text-[13px] text-muted-foreground">
        {favicon && (
          <img src={favicon} alt="" className="w-4 h-4" />
        )}
        <span className="truncate block max-w-full">{new URL(url).hostname}</span>
      </div>

      {/* Title */}
      <a
        href={url}
        className="
           text-[18px] sm:text-[20px]
          text-blue-600 dark:text-blue-400
          hover:underline
          block mb-1
                "
      >
        {title}
      </a>

      {/* Description */}
      <p
        className="text-[13px] sm:text-[14px] text-muted-foreground leading-relaxed line-clamp-3"
        dangerouslySetInnerHTML={{ __html: highlightText(description) }}
      />
    </div>
  );
}