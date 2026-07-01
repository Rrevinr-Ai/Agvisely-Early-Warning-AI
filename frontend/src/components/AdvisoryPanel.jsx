import { useState } from "react";
import { api } from "../api";

export default function AdvisoryPanel() {
  const [form, setForm] = useState({
    crop: "rice",
    district: "",
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
        ...form,
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
        <p>সরাসরি API থেকে আবহাওয়া ও ফসল পরামর্শ দেখুন</p>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          ফসল
          <input value={form.crop} onChange={(e) => update("crop", e.target.value)} />
        </label>
        <label>
          জেলা
          <input
            value={form.district}
            onChange={(e) => update("district", e.target.value)}
          />
        </label>
        <label>
          উপজেলা
          <input
            value={form.upazila}
            onChange={(e) => update("upazila", e.target.value)}
          />
        </label>
        <button type="submit" className="primary full" disabled={loading}>
          {loading ? "লোড হচ্ছে..." : "পরামর্শ আনুন"}
        </button>
      </form>

      {error && <div className="alert error">{error}</div>}

      {result && (
        <div className="json-card">
          <h3>{result.crop} — {result.location}</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}
