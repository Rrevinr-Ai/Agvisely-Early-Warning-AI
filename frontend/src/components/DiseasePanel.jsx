import { useEffect, useState } from "react";
import { api } from "../api";
import SpeakButton from "./SpeakButton";

export default function DiseasePanel() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [data, setData] = useState(null);

  useEffect(() => {
    api
      .getWheatDisease()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>গম রোগ পূর্বাভাস</h2>
        <p>Pre-season ২০২৬-২৭ — Leaf Rust ও Wheat Blast (CIMMYT advisory)</p>
      </div>

      {loading && <p>লোড হচ্ছে...</p>}
      {error && <div className="alert error">{error}</div>}

      {data && (
        <div className="disease-list">
          <p className="general">{data.general_advisory_bn}</p>
          {data.varieties_priority_bn && (
            <p className="general">{data.varieties_priority_bn}</p>
          )}
          {data.agent_speech && (
            <div className="agent-speech">
              <h3>সংক্ষিপ্ত কথ্য পরামর্শ</h3>
              <p>{data.agent_speech}</p>
              <SpeakButton text={data.agent_speech} />
            </div>
          )}
          {data.diseases.map((item) => (
            <article key={item.name} className="disease-card">
              <div className="disease-top">
                <h3>{item.name_bn || item.name}</h3>
                <span className={`risk ${item.risk_level}`}>{item.risk_level}</span>
              </div>
              {item.symptoms_bn && (
                <p>
                  <strong>লক্ষণ:</strong> {item.symptoms_bn}
                </p>
              )}
              <p>
                <strong>পরামর্শ:</strong> {item.advisory_bn}
              </p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
