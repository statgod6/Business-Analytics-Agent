import { useEffect, useState } from "react";
import { Focus } from "lucide-react";

export default function FocusModeToggle() {
  const [enabled, setEnabled] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("focus-mode", enabled);
  }, [enabled]);

  return (
    <button
      onClick={() => setEnabled((p: boolean) => !p)}
      title={enabled ? "Exit focus mode" : "Focus mode: show only active decision"}
      className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs transition-colors ${
        enabled
          ? "bg-emerald-500/20 text-emerald-400"
          : "text-slate-500 hover:bg-slate-800 hover:text-slate-300"
      }`}
    >
      <Focus size={12} />
      <span className="hidden sm:inline">{enabled ? "Focus On" : "Focus"}</span>
    </button>
  );
}