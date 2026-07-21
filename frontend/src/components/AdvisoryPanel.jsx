import { useState } from "react";
import { api } from "../api";
import SpeakButton from "./SpeakButton";

const crops = [
  { value: "aman rice", label: "আমন ধান" },
  { value: "rice", label: "ধান" },
  { value: "wheat", label: "গম" },
  { value: "maize", label: "ভুট্টা" },
  { value: "potato", label: "আলু" },
  { value: "jute", label: "পাট" },
];

function AdvisorySpeech({ advisory }) {
  if (!advisory || typeof advisory !== "object") return null;

  const speech =
    advisory.agent_speech ||
    advisory.message ||
    (Array.isArray(advisory.advisory_bn) ? advisory.advisory_bn.join("\n\n") : null);

  const source = advisory.source || "unknown";
  const sourceLabel =
    source === "excel"
      ? "Excel নিয়ম"
      : source === "gpt_backup"
        ? "GPT backup"
        : source;

  return (
    <div className="advisory-result">
      <div className="advisory-meta">
        <span className={`source-badge source-${source}`}>{sourceLabel}</span>
        {advisory.stage_bn || advisory.stage ? (
          <span className="stage-badge">
            {advisory.stage_bn || advisory.stage}
          </span>
        ) : null}
        {advisory.crop_bn || advisory.crop ? (
          <span className="stage-badge">{advisory.crop_bn || advisory.crop}</span>
        ) : null}
      </div>

      {speech ? (
        <div className="agent-speech">
          <h3>পরামর্শ</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{speech}</p>
          <SpeakButton text={speech} />
        </div>
      ) : (
        <pre>{JSON.stringify(advisory, null, 2)}</pre>
      )}

      {Array.isArray(advisory.matched_categories) && advisory.matched_categories.length > 0 && (
        <p className="muted-line">
          মিল: {advisory.matched_categories.join(", ")}
        </p>
      )}
    </div>
  );
}

export default function AdvisoryPanel() {
  const [form, setForm] = useState({
    crop: "aman rice",
    district: "Rangpur",
    upazila: "",
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
      const data = await api.getAdvisory({
        crop: form.crop,
        district: form.district || undefined,
        upazila: form.upazila || undefined,
      });
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
        <h2>Agvisely পরামর্শ</h2>
        <p>
          Excel নিয়ম আগে, না মিললে GPT fallback — আমন ধানের জন্য স্টেজ/আবহাওয়া ম্যাট্রিক্স
        </p>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          ফসল
          <select value={form.crop} onChange={(e) => update("crop", e.target.value)}>
            {crops.map((crop) => (
              <option key={crop.value} value={crop.value}>
                {crop.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          জেলা
          <input
            value={form.district}
            onChange={(e) => update("district", e.target.value)}
            placeholder="যেমন Rangpur"
          />
        </label>
        <label>
          উপজেলা
          <input
            value={form.upazila}
            onChange={(e) => update("upazila", e.target.value)}
            placeholder="ঐচ্ছিক"
          />
        </label>
        <button type="submit" className="primary full" disabled={loading}>
          {loading ? "লোড হচ্ছে..." : "পরামর্শ আনুন"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="json-card">
          <h3>
            {result.crop} — {result.location}
          </h3>
          <AdvisorySpeech advisory={result.advisory} />
          <details className="raw-details">
            <summary>Raw JSON</summary>
            <pre>{JSON.stringify(result, null, 2)}</pre>
          </details>
        </div>
      )}
    </section>
  );
}
