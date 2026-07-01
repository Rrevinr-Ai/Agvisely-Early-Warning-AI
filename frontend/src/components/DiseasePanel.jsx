import { useEffect, useState } from "react";
import { api } from "../api";

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
        <p>Pre-season static disease advisory</p>
      </div>

      {loading && <p>লোড হচ্ছে...</p>}
      {error && <div className="alert error">{error}</div>}

      {data && (
        <div className="disease-list">
          <p className="general">{data.general_advisory_bn}</p>
          {data.diseases.map((item) => (
            <article key={item.name} className="disease-card">
              <div className="disease-top">
                <h3>{item.name}</h3>
                <span className={`risk ${item.risk_level}`}>{item.risk_level}</span>
              </div>
              <p>{item.advisory_bn}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
