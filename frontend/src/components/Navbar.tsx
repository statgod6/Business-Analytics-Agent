import { useAuth } from "../hooks/useAuth";
import { useNavigate } from "react-router-dom";
import FocusModeToggle from "./FocusModeToggle";
import { LogOut, User as UserIcon } from "lucide-react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-800 bg-slate-900/80 px-4 backdrop-blur md:px-6">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-emerald-500 text-sm font-bold text-slate-950">
          BA
        </div>
        <span className="text-sm font-semibold text-slate-100">BA Agent</span>
      </div>

      <div className="flex items-center gap-4">
        <FocusModeToggle />
        <div className="flex items-center gap-2 text-sm text-slate-400">
          <UserIcon size={14} />
          <span className="hidden sm:inline">{user?.email}</span>
        </div>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-sm text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
        >
          <LogOut size={14} />
          <span className="hidden sm:inline">Logout</span>
        </button>
      </div>
    </header>
  );
}