interface QuickSuggestionProps {
  label: string;
}

export function QuickSuggestion({ label }: QuickSuggestionProps) {
  return (
    <button
      className="
        px-5 py-2.5 
        bg-secondary/50 hover:bg-secondary 
        text-secondary-foreground/80 hover:text-secondary-foreground
        rounded-full 
        text-[14px]
        transition-all duration-200
        hover:shadow-[0_2px_6px_rgba(0,0,0,0.1)]
        cursor-pointer
      "
    >
      {label}
    </button>
  );
}
