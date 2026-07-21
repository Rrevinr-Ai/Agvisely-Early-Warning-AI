import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { createWavRecorder, wavToBase64 } from "../utils/audioRecorder";
import SpeakButton from "./SpeakButton";

const crops = [
  { value: "aman rice", label: "আমন ধান" },
  { value: "rice", label: "ধান (সাধারণ)" },
  { value: "wheat", label: "গম" },
  { value: "maize", label: "ভুট্টা" },
  { value: "potato", label: "আলু" },
  { value: "jute", label: "পাট" },
];

const intentLabels = {
  weather: "আবহাওয়া",
  advisory: "ফসল পরামর্শ",
  disease: "রোগ",
  conversation: "সাধারণ",
  error: "ত্রুটি",
};

const quickQuestions = [
  "I am a rice farmer from Babuganj. Is there any weather advisory for me for next 5 days?",
  "I am a rice farmer from Rangpur Sadar. Is there any weather advisory for me for next 5 days?",
  "Is there any other information that you can provide?",
  "I want to cultivate wheat in the upcoming season. Is there any advisory that you can provide?",
  "মাটি পরীক্ষায় টাকা নেই, তাহলে কী করব?",
];

function createSessionId() {
  return crypto.randomUUID();
}

export default function CallPanel({ onCallComplete }) {
  const [sessionId, setSessionId] = useState(createSessionId);
  const [callActive, setCallActive] = useState(true);
  const [form, setForm] = useState({
    phone_number: "01712345678",
    district: "",
    upazila: "",
    crop: "aman rice",
  });
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [recording, setRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [error, setError] = useState("");
  const wavRecorderRef = useRef(null);
  const recordingRef = useRef(false);
  const chatEndRef = useRef(null);
  const recordingStartRef = useRef(null);
  const recordingTimerRef = useRef(null);

  const hotlineNumber = import.meta.env.VITE_TWILIO_PHONE || "+880XXXXXXXXXX";
  const publicUrl = import.meta.env.VITE_PUBLIC_BASE_URL || "";

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [conversation, loading]);

  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
    };
  }, []);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const sendQuestion = async (text, { fromVoice = false } = {}) => {
    if (!text?.trim()) return;

    setLoading(true);
    setError("");

    setConversation((prev) => [
      ...prev,
      { role: "user", text: text.trim(), isVoice: fromVoice },
    ]);

    try {
      const payload = {
        phone_number: form.phone_number,
        question_text: text.trim(),
        web_session_id: sessionId,
        district: form.district || undefined,
        upazila: form.upazila || undefined,
        crop: form.crop,
      };

      const data = await api.askAgent(payload);
      setConversation((prev) => [
        ...prev,
        { role: "agent", text: data.response_text, intent: data.intent, callId: data.id },
      ]);
      onCallComplete?.(data);
      setQuestion("");
    } catch (err) {
      setError(err.message);
      setConversation((prev) => prev.slice(0, -1));
    } finally {
      setLoading(false);
    }
  };

  const sendVoice = async (audioBase64) => {
    setLoading(true);
    setError("");

    try {
      const payload = {
        phone_number: form.phone_number,
        audio_base64: audioBase64,
        web_session_id: sessionId,
        district: form.district || undefined,
        upazila: form.upazila || undefined,
        crop: form.crop,
      };

      const data = await api.askAgent(payload);
      const heard = data.question_text?.trim();
      if (!heard) {
        throw new Error("শুনতে পারিনি — আবার বলুন");
      }

      setConversation((prev) => [
        ...prev,
        { role: "user", text: heard, isVoice: true },
        { role: "agent", text: data.response_text, intent: data.intent, callId: data.id },
      ]);
      onCallComplete?.(data);
      setQuestion("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setTranscribing(false);
    }
  };

  const transcribeAndSend = async (audioBase64) => {
    setTranscribing(true);
    await sendVoice(audioBase64);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    sendQuestion(question);
  };

  const startRecording = async () => {
    setError("");
    try {
      const recorder = createWavRecorder();
      await recorder.start();
      wavRecorderRef.current = recorder;
      recordingRef.current = true;
      recordingStartRef.current = Date.now();
      recordingTimerRef.current = setInterval(() => {
        const seconds = Math.floor((Date.now() - recordingStartRef.current) / 1000);
        setRecordingSeconds(seconds);
        if (seconds >= 12) stopRecording();
      }, 200);
      setRecording(true);
    } catch {
      setError("মাইক্রোফোন access পাওয়া যায়নি");
    }
  };

  const stopRecording = async () => {
    if (!wavRecorderRef.current || !recordingRef.current) return;

    recordingRef.current = false;
    setRecording(false);
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }

    const elapsed = Date.now() - (recordingStartRef.current || 0);
    setRecordingSeconds(0);

    if (elapsed < 1500) {
      setError("কমপক্ষে ২ সেকেন্ড বলুন");
      wavRecorderRef.current = null;
      return;
    }

    try {
      const wavBuffer = await wavRecorderRef.current.stop();
      wavRecorderRef.current = null;

      if (wavBuffer.byteLength < 5000) {
        setError("অডিও খুব ছোট — আরেকটু বলুন");
        return;
      }

      const base64 = await wavToBase64(wavBuffer);
      await transcribeAndSend(base64);
    } catch (err) {
      if (err?.message === "SILENT_AUDIO") {
        setError("মাইক্রোফোনে কথা শোনা যায়নি — কাছে এসে স্পষ্ট করে বলুন");
      } else {
        setError("রেকording ব্যর্থ — আবার চেষ্টা করুন");
      }
      wavRecorderRef.current = null;
    }
  };

  const endCall = () => {
    setCallActive(false);
    setConversation([]);
    setSessionId(createSessionId());
    setCallActive(true);
    setQuestion("");
    setError("");
  };

  return (
    <section className="panel call-panel">
      <div className="panel-header">
        <h2>AI কল এজেন্ট</h2>
        <p>
          CIMMYT demo: Babuganj (থোড়, ৪৪মিমি/&gt;৩৫°C) ও Rangpur Sadar (কুশি, ১০মিমি) —
          আলাদা কৃষকের জন্য “কল শেষ” করে নতুন session নিন
        </p>
      </div>

      <div className="call-info-grid">
        <article className="call-info-card">
          <h3>Web Simulation</h3>
          <p>Excel নিয়ম + কথোপকথন বুঝে উত্তর — একই session-এ আগের কথা রাখে</p>
          <span className="call-badge">Session: {sessionId.slice(0, 8)}...</span>
        </article>
        <article className="call-info-card">
          <h3>Real Phone Call</h3>
          <p>Twilio hotline configure করলে farmer সরাসরি call করতে পারবে</p>
          <strong className="hotline">{hotlineNumber}</strong>
          {publicUrl && (
            <span className="call-badge">{publicUrl}/telephony/incoming</span>
          )}
        </article>
      </div>

      <form className="form-grid call-form" onSubmit={handleSubmit}>
        <label>
          ফোন নম্বর
          <input
            value={form.phone_number}
            onChange={(e) => update("phone_number", e.target.value)}
            required
          />
        </label>
        <label>
          জেলা
          <input
            value={form.district}
            onChange={(e) => update("district", e.target.value)}
            placeholder="ঐচ্ছিক — কথায় বললে সেটা প্রাধান্য পাবে"
          />
        </label>
        <label>
          উপজেলা
          <input value={form.upazila} onChange={(e) => update("upazila", e.target.value)} />
        </label>
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
      </form>

      <div className="quick-questions">
        {quickQuestions.map((q) => (
          <button
            key={q}
            type="button"
            className="chip"
            disabled={loading || transcribing}
            onClick={() => sendQuestion(q)}
          >
            {q}
          </button>
        ))}
      </div>

      <div className="call-chat">
        {conversation.length === 0 && (
          <p className="chat-empty">
            কল শুরু — জেলা, ফসল ও পর্যায় (কুশি/থোড়) বলে প্রশ্ন করুন; পরে follow-up দিতে পারবেন
          </p>
        )}

        {conversation.map((msg, index) => (
          <div key={index} className={`chat-bubble ${msg.role}`}>
            {msg.role === "user" && msg.isVoice && (
              <div className="chat-meta">
                <span>আপনি বলেছেন</span>
              </div>
            )}
            {msg.role === "agent" && (
              <div className="chat-meta">
                <span>{intentLabels[msg.intent] || msg.intent}</span>
                {msg.callId && <span>Call #{msg.callId}</span>}
              </div>
            )}
            <p>{msg.text}</p>
            {msg.role === "agent" && (
              <div className="speak-row">
                <SpeakButton text={msg.text} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-bubble agent loading-bubble">
            <p>পরামর্শ তৈরি হচ্ছে...</p>
          </div>
        )}

        {transcribing && (
          <div className="chat-bubble agent loading-bubble">
            <p>শুনছি এবং পাঠাচ্ছি...</p>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {error && <div className="alert error">{error}</div>}

      <div className="call-actions">
        <input
          className="call-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="বাংলায় প্রশ্ন লিখুন বা মাইক দিয়ে বলুন..."
          disabled={loading || transcribing || !callActive}
        />
        <button
          type="button"
          className={`secondary ${recording ? "recording" : ""}`}
          onClick={recording ? stopRecording : startRecording}
          disabled={loading || transcribing}
        >
          {recording ? `থামান (${recordingSeconds}s)` : "বলুন"}
        </button>
        <button
          type="button"
          className="primary"
          disabled={loading || transcribing || !question.trim()}
          onClick={() => sendQuestion(question)}
        >
          পাঠান
        </button>
        <button type="button" className="secondary danger" onClick={endCall}>
          কল শেষ
        </button>
      </div>
    </section>
  );
}
