import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

export default function Navbar() {
  const { hr, token, logout } = useAuth();
  const location = useLocation();

  const showAuthLinks = location.pathname !== "/login" && location.pathname !== "/signup";

  return (
    <header className="bg-white border-b border-slate-200">
      <nav className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link to={token ? "/dashboard" : "/login"} className="flex items-center gap-2">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold">
            AI
          </span>
          <span className="font-semibold text-slate-900">
            Resume Evaluator
          </span>
        </Link>
        {showAuthLinks && (
          <div className="flex items-center gap-4">
            {hr && (
              <span className="text-sm text-slate-600">
                Signed in as <span className="font-medium">{hr.name}</span>
              </span>
            )}
            {token ? (
              <button
                onClick={logout}
                className="text-sm px-3 py-1.5 rounded-md border border-slate-300 hover:bg-slate-50"
              >
                Logout
              </button>
            ) : (
              <Link
                to="/login"
                className="text-sm px-3 py-1.5 rounded-md border border-slate-300 hover:bg-slate-50"
              >
                Login
              </Link>
            )}
          </div>
        )}
      </nav>
    </header>
  );
}

