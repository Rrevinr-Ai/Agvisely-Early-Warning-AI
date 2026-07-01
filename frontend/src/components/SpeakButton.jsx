import { useState } from "react";
import { api } from "../api";

export default function SpeakButton({ text }) {
  const [loading, setLoading] = useState(false);

  const handleSpeak = async () => {
    if (!text?.trim()) return;
    setLoading(true);
    try {
      const { audio_base64 } = await api.speak({ text });
      const audio = new Audio(`data:audio/mp3;base64,${audio_base64}`);
      await audio.play();
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button type="button" className="secondary" onClick={handleSpeak} disabled={loading || !text}>
      {loading ? "শোনানো হচ্ছে..." : "🔊 শুনুন"}
    </button>
  );
}
