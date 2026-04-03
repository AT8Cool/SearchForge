import { Link } from 'react-router';

export function Header() {
  return (
    <header className="relative z-20 w-full px-12 py-6">
      <nav className="flex justify-end items-center gap-8">
        <Link 
          to="/about"
          className="text-[15px] text-foreground/70 hover:text-foreground transition-colors duration-200"
        >
          About
        </Link>
      </nav>
    </header>
  );
}
