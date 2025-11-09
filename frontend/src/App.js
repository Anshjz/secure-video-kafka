import React, { useState, useEffect } from "react";

function App() {
  const [file, setFile] = useState(null);
  const [videos, setVideos] = useState([]);
  const [progress, setProgress] = useState(0);
  const [currentVideo, setCurrentVideo] = useState(null);

  const backend = "http://127.0.0.1:8000";

  // 🟢 Fetch uploaded videos
  async function fetchVideos() {
    const res = await fetch(`${backend}/videos`);
    const json = await res.json();
    setVideos(json);
  }

  useEffect(() => {
    fetchVideos();
  }, []);

  // 🟢 Upload file with progress bar
  async function uploadFile() {
    if (!file) return alert("Pick a file first!");

    const fd = new FormData();
    fd.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${backend}/upload`, true);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setProgress(percent);
      }
    };

    xhr.onload = () => {
      if (xhr.status === 200) {
        alert("✅ Uploaded successfully!");
        setProgress(0);
        setFile(null);
        fetchVideos();
      } else {
        alert("❌ Upload failed!");
      }
    };

    xhr.send(fd);
  }

  // 🟠 Delete video
  async function deleteVideo(id) {
    const confirmDelete = window.confirm("Are you sure you want to delete this video?");
    if (!confirmDelete) return;

    const res = await fetch(`${backend}/delete/${id}`, { method: "DELETE" });
    if (res.ok) {
      alert("🗑️ Deleted successfully!");
      fetchVideos();
    } else {
      alert("❌ Failed to delete video!");
    }
  }

  return (
    <div style={{ padding: 20, fontFamily: "Arial" }}>
      <h2>🎥 Secure Video Upload & Stream via FastAPI + Kafka</h2>
      <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={uploadFile}>Upload</button>

      {/* Progress bar */}
      {progress > 0 && (
        <div style={{ width: "300px", background: "#eee", marginTop: 10 }}>
          <div
            style={{
              width: `${progress}%`,
              background: "green",
              height: "10px",
              transition: "width 0.3s",
            }}
          />
          <p>{progress}%</p>
        </div>
      )}

      <hr />

      <h3>Uploaded Videos</h3>
      {videos.length === 0 && <p>No videos uploaded yet.</p>}
      <ul>
        {videos.map((v) => (
          <li key={v.id} style={{ marginBottom: "10px" }}>
            <b>{v.filename}</b>{" "}
            <button onClick={() => setCurrentVideo(v)}>▶ Play</button>{" "}
            <button onClick={() => deleteVideo(v.id)} style={{ color: "red" }}>
              🗑 Delete
            </button>
          </li>
        ))}
      </ul>

      <hr />
      <h3>Now Playing:</h3>
      {currentVideo ? (
        <video
          key={currentVideo.unique_filename}
          controls
          width="720"
          src={`${backend}/stream?filename=${currentVideo.unique_filename}`}
        />
      ) : (
        <p>No video selected</p>
      )}
    </div>
  );
}

export default App;
