import { useEffect, useState } from "react";
import { api } from "./api";
import CallPanel from "./components/CallPanel";
import FarmerForm from "./components/FarmerForm";
import AdvisoryPanel from "./components/AdvisoryPanel";
import WeatherPanel from "./components/WeatherPanel";
import DiseasePanel from "./components/DiseasePanel";
import SurveyForm from "./components/SurveyForm";

const tabs = [
  { id: "call", label: "কল এজেন্ট" },
  { id: "farmer", label: "কৃষক" },
  { id: "weather", label: "আবহাওয়া" },
  { id: "advisory", label: "পরামর্শ" },
  { id: "disease", label: "গম রোগ" },
  { id: "survey", label: "মূল্যায়ন" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("call");
  const [status, setStatus] = useState("checking");
  const [lastCallId, setLastCallId] = useState(null);

  useEffect(() => {
    api
      .health()
      .then(() => setStatus("online"))
      .catch(() => setStatus("offline"));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div>
          <p className="eyebrow">CIMMYT · Agvisely</p>
          <h1>কৃষি সহায়তা এজেন্ট</h1>
          <p className="subtitle">
            বাংলায় আবহাওয়া ও ফসল পরামর্শ — Excel নিয়ম + কথোপকথন বুঝে উত্তর
          </p>
        </div>
        <div className={`status-pill ${status}`}>
          {status === "online" ? "সার্ভার চালু" : status === "offline" ? "সার্ভার বন্ধ" : "..."}
        </div>
      </header>

      <nav className="tabs">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={activeTab === tab.id ? "active" : ""}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="content">
        {activeTab === "call" && (
          <CallPanel onCallComplete={(call) => setLastCallId(call.id)} />
        )}
        {activeTab === "farmer" && <FarmerForm />}
        {activeTab === "weather" && <WeatherPanel />}
        {activeTab === "advisory" && <AdvisoryPanel />}
        {activeTab === "disease" && <DiseasePanel />}
        {activeTab === "survey" && <SurveyForm lastCallId={lastCallId} />}
      </main>
    </div>
  );
}
