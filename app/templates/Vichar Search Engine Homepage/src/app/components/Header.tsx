export function Header() {
  return (
    <header className="w-full px-12 py-6">
      <nav className="flex justify-end items-center gap-8">
        <a 
          href="#about" 
          className="text-[15px] text-foreground/70 hover:text-foreground transition-colors duration-200"
        >
          About
        </a>
      </nav>
    </header>
  );
}