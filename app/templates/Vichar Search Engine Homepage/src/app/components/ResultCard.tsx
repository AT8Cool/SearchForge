interface ResultCardProps {
  title: string;
  url: string;
  description: string;
}

export function ResultCard({ title, url, description }: ResultCardProps) {
  return (
    <div className="py-4 group">
      {/* URL */}
      <div className="text-[13px] text-muted-foreground/70 mb-1">
        {url}
      </div>
      
      {/* Title */}
      <a 
        href={url}
        className="text-[20px] text-blue-600 dark:text-blue-400 hover:underline transition-all block mb-1"
      >
        {title}
      </a>
      
      {/* Description */}
      <p className="text-[14px] text-muted-foreground leading-relaxed line-clamp-2">
        {description}
      </p>
    </div>
  );
}
