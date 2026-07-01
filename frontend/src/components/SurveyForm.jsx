import { useEffect, useState } from "react";
import { api } from "../api";

const scoreLabels = {
  1: "১ — খুব কম",
  2: "২ — কম",
  3: "৩ — মোটামোটি",
  4: "৪ — ভালো",
  5: "৫ — খুব ভালো",
};

function ScoreSelect({ label, value, onChange }) {
  return (
    <label className="full">
      {label}
      <select value={value} onChange={(e) => onChange(Number(e.target.value))}>
        {[1, 2, 3, 4, 5].map((score) => (
          <option key={score} value={score}>
            {scoreLabels[score]}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function SurveyForm({ lastCallId }) {
  const [form, setForm] = useState({
    call_id: "",
    comprehension_score: 4,
    trust_score: 4,
    adopted_practice: false,
    feedback_text: "",
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (lastCallId) {
      setForm((prev) => ({ ...prev, call_id: String(lastCallId) }));
    }
  }, [lastCallId]);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");

    try {
      const payload = {
        call_id: form.call_id ? Number(form.call_id) : undefined,
        comprehension_score: Number(form.comprehension_score),
        trust_score: Number(form.trust_score),
        adopted_practice: form.adopted_practice,
        feedback_text: form.feedback_text.trim() || undefined,
      };
      const data = await api.submitSurvey(payload);
      setMessage(`মূল্যায়ন সফলভাবে জমা হয়েছে — নম্বর: ${data.id}`);
      setForm((prev) => ({
        ...prev,
        adopted_practice: false,
        feedback_text: "",
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>কৃষক মূল্যায়ন</h2>
        <p>
          কলের পর কৃষকের বোঝাপড়া, বিশ্বাস, পরামর্শ গ্রহণ ও মতামত রেকর্ড করুন
        </p>
      </div>

      {lastCallId && (
        <div className="alert success">
          সর্বশেষ কল #{lastCallId} — এই কলের জন্য মূল্যায়ন দিতে পারেন
        </div>
      )}

      <form className="form-grid" onSubmit={handleSubmit}>
        <label>
          কল নম্বর (Call ID)
          <input
            value={form.call_id}
            onChange={(e) => update("call_id", e.target.value)}
            placeholder="যেমন: ১"
            inputMode="numeric"
          />
        </label>

        <label>
          &nbsp;
          <span className="field-hint">
            {form.call_id
              ? `কল #${form.call_id}-এর মূল্যায়ন`
              : "কল এজেন্ট tab থেকে কল করলে ID auto-fill হবে"}
          </span>
        </label>

        <ScoreSelect
          label="বোঝাপড়া — পরামর্শ কতটা বুঝেছেন?"
          value={form.comprehension_score}
          onChange={(value) => update("comprehension_score", value)}
        />

        <ScoreSelect
          label="বিশ্বাস — পরামর্শে কতটা বিশ্বাস করেছেন?"
          value={form.trust_score}
          onChange={(value) => update("trust_score", value)}
        />

        <label className="checkbox full">
          <input
            type="checkbox"
            checked={form.adopted_practice}
            onChange={(e) => update("adopted_practice", e.target.checked)}
          />
          দেওয়া পরামর্শ অনুসরণ করেছেন
        </label>

        <label className="full">
          অতিরিক্ত মতামত (ঐচ্ছিক)
          <textarea
            rows={4}
            value={form.feedback_text}
            onChange={(e) => update("feedback_text", e.target.value)}
            placeholder="কৃষক কী বললেন, কোন পরামর্শ কাজে লাগল..."
          />
        </label>

        <button type="submit" className="primary full" disabled={loading}>
          {loading ? "জমা হচ্ছে..." : "মূল্যায়ন জমা দিন"}
        </button>
      </form>

      {message && <div className="alert success">{message}</div>}
      {error && <div className="alert error">{error}</div>}
    </section>
  );
}
