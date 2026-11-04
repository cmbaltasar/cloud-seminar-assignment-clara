import { useEffect, useState } from "react";

// Notes are stored by the API in Postgres: reload the page and they're still there.
export default function Notes({ apiUrl }) {
  const [notes, setNotes] = useState([]);
  const [text, setText] = useState("");
  const [error, setError] = useState(null);

  function loadNotes() {
    fetch(`${apiUrl}/api/notes`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setNotes(data);
        setError(null);
      })
      .catch((err) => setError(`Could not load notes (${err.message})`));
  }

  useEffect(loadNotes, [apiUrl]);

  function addNote(event) {
    event.preventDefault();
    fetch(`${apiUrl}/api/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setText("");
        loadNotes();
      })
      .catch((err) => setError(`Could not save the note (${err.message})`));
  }

  return (
    <section>
      <h2>Notes</h2>
      <form onSubmit={addNote}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Write a note…"
          maxLength={500}
          required
        />
        <button type="submit">Add</button>
      </form>
      {error && <p className="error">{error}</p>}
      {notes.length === 0 && !error && <p className="muted">No notes yet.</p>}
      <ul>
        {notes.map((note) => (
          <li key={note.id}>
            {note.text}
            <span className="muted"> · {new Date(note.created_at).toLocaleString()}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
