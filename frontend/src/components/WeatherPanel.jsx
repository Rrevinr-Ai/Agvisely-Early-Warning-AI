import { useState } from "react";
import { api } from "../api";
import SpeakButton from "./SpeakButton";

function WeatherDetails({ weather }) {
  if (weather.source === "fallback") {
    return (
      <div className="alert error">
        {weather.summary || "এই মুহূর্তে Agvisely থেকে আবহাওয়ার তথ্য পাওয়া যাচ্ছে না।"}
      </div>
    );
  }

  const agentSpeech = weather.agent_speech || weather.summary;
  const speakText = agentSpeech || "";

  const fields = [
    ["temperature", "তাপমাত্রা"],
    ["season_bn", "মৌসুম"],
    ["weather_condition", "আবহাওয়া"],
    ["rainfall_outlook", "বৃষ্টির সম্ভাবনা"],
    ["crops_to_plant", "এখন যে ফসল লাগান"],
    ["crops_to_harvest", "যে ফসল কাটতে হবে"],
    ["urgent_actions", "এই সপ্তাহে করণীয়"],
  ];

  const known = fields.filter(([key]) => weather[key] != null && weather[key] !== "");

  return (
    <>
      {weather.source === "gpt_backup" && weather.disclaimer && (
        <div className="alert success">{weather.disclaimer}</div>
      )}

      {agentSpeech && (
        <div className="agent-speech">
          <h3>কৃষি এজেন্ট বলছেন</h3>
          <p className="answer">{agentSpeech}</p>
          <div className="speak-row">
            <SpeakButton text={speakText} />
          </div>
        </div>
      )}

      {known.length > 0 && (
        <div className="weather-grid">
          {known.map(([key, label]) => (
            <article key={key} className="weather-card">
              <span className="weather-label">{label}</span>
              <strong className="weather-value">{String(weather[key])}</strong>
            </article>
          ))}
        </div>
      )}

      {!agentSpeech && known.length === 0 && (
        <div className="json-card">
          <pre>{JSON.stringify(weather, null, 2)}</pre>
        </div>
      )}
    </>
  );
}

export default function WeatherPanel() {
  const [form, setForm] = useState({
    district: "",
    upazila: "",
    latitude: "",
    longitude: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const payload = {
        district: form.district || undefined,
        upazila: form.upazila || undefined,
        latitude: form.latitude ? Number(form.latitude) : undefined,
        longitude: form.longitude ? Number(form.longitude) : undefined,
      };
      const data = await api.getWeather(payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>আবহাওয়া ও কৃষি পরামর্শ</h2>
        <p>এলাকার তাপমাত্রা, ফসল লাগানো ও কাটার পরামর্শ — যেন একজন কৃষি এজেন্ট বলছে</p>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          জেলা
          <input
            value={form.district}
            onChange={(e) => update("district", e.target.value)}
            placeholder="যেমন: Faridpur"
          />
        </label>
        <label>
          উপজেলা
          <input
            value={form.upazila}
            onChange={(e) => update("upazila", e.target.value)}
            placeholder="যেমন: Modhukhali"
          />
        </label>
        <label>
          Latitude
          <input
            value={form.latitude}
            onChange={(e) => update("latitude", e.target.value)}
            placeholder="23.8103"
            type="number"
            step="any"
          />
        </label>
        <label>
          Longitude
          <input
            value={form.longitude}
            onChange={(e) => update("longitude", e.target.value)}
            placeholder="90.4125"
            type="number"
            step="any"
          />
        </label>
        <button type="submit" className="primary full" disabled={loading}>
          {loading ? "এজেন্ট ভাবছে..." : "পরামর্শ নিন"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="result-card">
          <div className="meta">
            <span>অবস্থান: {result.location}</span>
            {result.weather.source === "gpt_backup" && <span>কৃষি এজেন্ট (GPT)</span>}
            {result.weather.source && result.weather.source !== "gpt_backup" && (
              <span>উৎস: {result.weather.source}</span>
            )}
          </div>
          <WeatherDetails weather={result.weather} />
        </div>
      )}
    </section>
  );
}
