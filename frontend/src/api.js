const API_BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg || JSON.stringify(item)).join(", ")
      : typeof detail === "object" && detail !== null
        ? JSON.stringify(detail)
        : detail || "Request failed";
    throw new Error(message);
  }
  return data;
}

export const api = {
  health: () => request("/"),
  registerFarmer: (body) =>
    request("/farmers/", { method: "POST", body: JSON.stringify(body) }),
  askAgent: (body) =>
    request("/calls/", { method: "POST", body: JSON.stringify(body) }),
  getAdvisory: (body) =>
    request("/advisory/", { method: "POST", body: JSON.stringify(body) }),
  getWeather: (body) =>
    request("/weather/", { method: "POST", body: JSON.stringify(body) }),
  getWheatDisease: () => request("/disease/wheat"),
  speak: (body) =>
    request("/speech/speak", { method: "POST", body: JSON.stringify(body) }),
  transcribe: (body) =>
    request("/speech/transcribe", { method: "POST", body: JSON.stringify(body) }),
  submitSurvey: (body) =>
    request("/surveys/", { method: "POST", body: JSON.stringify(body) }),
};
