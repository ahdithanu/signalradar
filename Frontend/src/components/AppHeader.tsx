import { Radar, BarChart3, Settings, Moon, Sun } from "lucide-react";
import { NavLink } from "./NavLink";
import { useEffect, useState } from "react";

const AppHeader = () => {
  const [dark, setDark] = useState(() =>
    typeof window !== "undefined" && document.documentElement.classList.contains("dark")
  );

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") setDark(true);
    else if (saved === "light") setDark(false);
    else if (window.matchMedia("(prefers-color-scheme: dark)").matches) setDark(true);
  }, []);

  return (
    <header className="border-b bg-card px-4 py-2.5 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Radar size={18} className="text-primary" />
        <span className="text-sm font-semibold text-foreground">Signal Radar</span>
        <span className="text-xs text-muted-foreground ml-1">GTM Intelligence</span>
      </div>
      <div className="flex items-center gap-2">
        <nav className="flex items-center gap-1">
          <NavLink
            to="/"
            className="text-xs px-3 py-1.5 rounded transition-colors text-muted-foreground hover:text-foreground hover:bg-secondary"
            activeClassName="bg-secondary text-foreground font-medium"
          >
            Dashboard
          </NavLink>
          <NavLink
            to="/analytics"
            className="text-xs px-3 py-1.5 rounded transition-colors text-muted-foreground hover:text-foreground hover:bg-secondary"
            activeClassName="bg-secondary text-foreground font-medium"
          >
            <span className="flex items-center gap-1">
              <BarChart3 size={12} />
              Analytics
            </span>
          </NavLink>
          <NavLink
            to="/settings"
            className="text-xs px-3 py-1.5 rounded transition-colors text-muted-foreground hover:text-foreground hover:bg-secondary"
            activeClassName="bg-secondary text-foreground font-medium"
          >
            <span className="flex items-center gap-1">
              <Settings size={12} />
              Settings
            </span>
          </NavLink>
        </nav>
        <button
          onClick={() => setDark((d) => !d)}
          className="p-1.5 rounded transition-colors text-muted-foreground hover:text-foreground hover:bg-secondary"
          aria-label="Toggle dark mode"
        >
          {dark ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    </header>
  );
};

export default AppHeader;
