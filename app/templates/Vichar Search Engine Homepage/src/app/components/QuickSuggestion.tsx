interface QuickSuggestionProps {
  label: string;
  onClick?: () => void;
}

export function QuickSuggestion({ label, onClick }: QuickSuggestionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="
        px-4 py-2.5
        bg-secondary/50 hover:bg-secondary
        text-secondary-foreground/80 hover:text-secondary-foreground
        rounded-full
        text-[14px]
        transition-all duration-200
        hover:shadow-[0_2px_6px_rgba(0,0,0,0.1)]
        cursor-pointer
        border border-border/30
        hover:-translate-y-0.5
      "
    >
      {label}
    </button>
  );
}
