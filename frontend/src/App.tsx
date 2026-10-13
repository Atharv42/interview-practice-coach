import React, { useState, useEffect } from "react";
import { Navbar } from "./components/Navbar";
import { RecordingStudio } from "./components/RecordingStudio";
import { MockInterviewStudio } from "./components/MockInterviewStudio";
import { SessionDetailView } from "./components/SessionDetailView";
import { SessionHistory } from "./components/SessionHistory";
import { AnalyticsDashboard } from "./components/AnalyticsDashboard";
import { SessionDetailResponse } from "./types";
import { api } from "./services/api";
import "./App.css";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"studio" | "mock" | "history" | "analytics">("studio");
  const [selectedSession, setSelectedSession] = useState<SessionDetailResponse | null>(null);
  const [isBackendHealthy, setIsBackendHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const health = await api.checkHealth();
        setIsBackendHealthy(health.status === "healthy");
      } catch {
        setIsBackendHealthy(false);
      }
    };
    checkConnection();
    const interval = setInterval(checkConnection, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSessionCreated = (session: SessionDetailResponse) => {
    setSelectedSession(session);
  };

  const handleSelectSession = async (sessionId: string) => {
    try {
      const detail = await api.getSession(sessionId);
      setSelectedSession(detail);
    } catch (err: unknown) {
      alert(`Could not load session details: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleBackToStudio = () => {
    setSelectedSession(null);
  };

  const handleSessionDeleted = () => {
    setSelectedSession(null);
    setActiveTab("history");
  };

  return (
    <div className="app-shell">
      <Navbar
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setSelectedSession(null);
          setActiveTab(tab);
        }}
        isBackendHealthy={isBackendHealthy}
      />

      <main className="main-content">
        {selectedSession ? (
          <SessionDetailView
            session={selectedSession}
            onBack={handleBackToStudio}
            onSessionDeleted={handleSessionDeleted}
          />
        ) : activeTab === "studio" ? (
          <RecordingStudio onSessionCreated={handleSessionCreated} />
        ) : activeTab === "mock" ? (
          <MockInterviewStudio onSelectSession={handleSelectSession} />
        ) : activeTab === "history" ? (
          <SessionHistory
            onSelectSession={handleSelectSession}
            onNavigateToStudio={() => setActiveTab("studio")}
          />
        ) : (
          <AnalyticsDashboard />
        )}
      </main>

      <footer className="footer">
        <div className="footer-container">
          <span>Interview Practice Coach &copy; {new Date().getFullYear()}</span>
          <span>Privacy Preserved &bull; Objective Multimodal Acoustic &amp; Geometric Analysis</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
