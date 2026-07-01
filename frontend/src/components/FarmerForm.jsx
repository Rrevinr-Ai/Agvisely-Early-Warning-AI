import { useState } from "react";
import { api } from "../api";

export default function FarmerForm() {
  const [form, setForm] = useState({
    phone_number: "",
    name: "",
    district: "",
    upazila: "",
    union_name: "",
    preferred_crop: "rice",
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");

    try {
      const data = await api.registerFarmer(form);
      setMessage(`কৃষক সংরক্ষিত — ID: ${data.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>কৃষক নিবন্ধন</h2>
        <p>ফোন নম্বর ও অবস্থান সংরক্ষণ করুন</p>
      </div>

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          ফোন নম্বর *
          <input
            value={form.phone_number}
            onChange={(e) => update("phone_number", e.target.value)}
            required
          />
        </label>
        <label>
          নাম
          <input value={form.name} onChange={(e) => update("name", e.target.value)} />
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
        <label>
          ইউনিয়ন
          <input
            value={form.union_name}
            onChange={(e) => update("union_name", e.target.value)}
          />
        </label>
        <label>
          পছন্দের ফসল
          <input
            value={form.preferred_crop}
            onChange={(e) => update("preferred_crop", e.target.value)}
          />
        </label>
        <button type="submit" className="primary full" disabled={loading}>
          {loading ? "সংরক্ষণ হচ্ছে..." : "সংরক্ষণ করুন"}
        </button>
      </form>

      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}
    </section>
  );
}
