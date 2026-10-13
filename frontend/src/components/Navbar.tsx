import React from "react";
import { Mic, History, TrendingUp, ShieldCheck, Activity } from "lucide-react";

interface NavbarProps {
  activeTab: "studio" | "history" | "analytics";
  setActiveTab: (tab: "studio" | "history" | "analytics") => void;
  isBackendHealthy: boolean | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isBackendHealthy,
}) => {
  return (
    <header className="navbar">
      <div className="navbar-container">
        <div className="navbar-brand">
          <div className="brand-icon">
            <Mic size={22} className="brand-mic" />
          </div>
          <div>
            <h1 className="brand-title">Interview Practice Coach</h1>
            <p className="brand-subtitle">Objective Multimodal Delivery Analytics</p>
          </div>
        </div>

        <nav className="navbar-links">
          <button
            type="button"
            className={`nav-button ${activeTab === "studio" ? "active" : ""}`}
            onClick={() => setActiveTab("studio")}
          >
            <Mic size={18} />
            <span>Practice Studio</span>
          </button>

          <button
            type="button"
            className={`nav-button ${activeTab === "history" ? "active" : ""}`}
            onClick={() => setActiveTab("history")}
          >
            <History size={18} />
            <span>Session History</span>
          </button>

          <button
            type="button"
            className={`nav-button ${activeTab === "analytics" ? "active" : ""}`}
            onClick={() => setActiveTab("analytics")}
          >
            <TrendingUp size={18} />
            <span>Analytics & Trends</span>
          </button>
        </nav>

        <div className="navbar-status">
          <div className="privacy-pill" title="Client-side privacy preservation: Raw video is never stored">
            <ShieldCheck size={16} className="text-emerald-500" />
            <span>Privacy Preserved</span>
          </div>

          <div
            className={`status-pill ${
              isBackendHealthy === true
                ? "healthy"
                : isBackendHealthy === false
                ? "offline"
                : "checking"
            }`}
            title="FastAPI Backend Health Status"
          >
            <Activity size={14} />
            <span>
              {isBackendHealthy === true
                ? "Backend Connected"
                : isBackendHealthy === false
                ? "Backend Offline"
                : "Connecting..."}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
