import type { Theme } from "./ThemeProvider";
import { useTheme } from "./ThemeProvider";

const OPTIONS: { value: Theme; label: string; icon: string }[] = [
  { value: "light", label: "Light", icon: "☀" },
  { value: "dark", label: "Dark", icon: "☾" },
  { value: "system", label: "System", icon: "◑" },
];

/**
 * Segmented Light / Dark / System control. Keyboard-accessible; the active
 * option is announced via aria-pressed.
 */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div
      role="group"
      aria-label="Theme"
      className="inline-flex items-center gap-1 rounded-lg border border-border bg-muted p-1"
    >
      {OPTIONS.map((opt) => {
        const active = theme === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            aria-pressed={active}
            title={opt.label}
            onClick={() => setTheme(opt.value)}
            className={`focus-ring flex h-8 w-8 items-center justify-center rounded-md text-sm transition-colors ${
              active
                ? "bg-card text-fg shadow-card"
                : "text-fg-muted hover:text-fg"
            }`}
          >
            <span aria-hidden>{opt.icon}</span>
            <span className="sr-only">{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
