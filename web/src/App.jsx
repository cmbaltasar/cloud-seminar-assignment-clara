import { useEffect, useState } from "react";
import Notes from "./Notes.jsx";

// Set in public/config.js at runtime (see index.html).
const API_URL = window.APP_CONFIG?.apiUrl ?? "http://localhost:8081";

export default function App() {
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_URL}/api/message`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setMessage(data.message))
      .catch((err) => setError(err.message));
  }, []);

  const status = message ? "connected" : error ? "unreachable" : "connecting…";

  return (
    <main>
      <h1>Cloud Seminar App</h1>

      <section>
        <h2>API</h2>
        <p>
          <span className={`dot ${message ? "ok" : "bad"}`} /> {status}
        </p>
        <p className="muted">API URL: {API_URL}</p>
      </section>

      <section>
        <h2>Message from the API</h2>
        {message && <p className="message">{message}</p>}
        {error && (
          <p className="error">
            Could not load the message ({error}). Is the API running, and does its
            CORS_ORIGIN allow this page's origin?
          </p>
        )}
        {!message && !error && <p className="muted">Loading…</p>}
      </section>

      <Notes apiUrl={API_URL} />
    </main>
  );
}
