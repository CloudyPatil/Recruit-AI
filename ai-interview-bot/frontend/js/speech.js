// ── Text to Speech ─────────────────────
function speak(text, onEnd) {
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.95;
  utterance.pitch = 1.0;
  utterance.lang = "en-US";
  utterance.onend = onEnd || null;
  speechSynthesis.speak(utterance);
}

// ── Audio Recording ─────────────────────
let mediaRecorder = null;
let audioChunks = [];
let audioStream = null;
let audioContext = null;
let analyser = null;
let silenceTimer = null;
let onSilenceCallback = null;

async function initMicrophone() {
  try {
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    // Setup audio analyser for silence detection
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(audioStream);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);
    
    console.log("✅ Mic ready");
    return true;
  } catch (err) {
    console.error("❌ Mic error:", err);
    return false;
  }
}

// ── Start recording with auto-stop on silence ──
function startRecordingWithAutoStop(onSilence) {
  if (!audioStream) return;
  
  audioChunks = [];
  mediaRecorder = new MediaRecorder(audioStream);
  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) audioChunks.push(e.data);
  };
  mediaRecorder.start();
  
  onSilenceCallback = onSilence;
  monitorSilence();
  console.log("🎤 Recording with auto-stop...");
}

// ── Monitor audio for silence ──
let speechDetected = false;
let silenceStart = null;
const SILENCE_THRESHOLD = 15;       // volume level
const SILENCE_DURATION = 3000;      // 3 sec silence = stop
const MIN_SPEECH_TIME = 2000;       // min 2 sec recording

let recordingStartTime = null;

function monitorSilence() {
  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  speechDetected = false;
  silenceStart = null;
  recordingStartTime = Date.now();
  
  function check() {
    if (!mediaRecorder || mediaRecorder.state !== "recording") return;
    
    analyser.getByteFrequencyData(dataArray);
    const avg = dataArray.reduce((a,b) => a+b, 0) / dataArray.length;
    const elapsed = Date.now() - recordingStartTime;
    
    if (avg > SILENCE_THRESHOLD) {
      // Speaking
      speechDetected = true;
      silenceStart = null;
    } else if (speechDetected && elapsed > MIN_SPEECH_TIME) {
      // Silence after speaking
      if (!silenceStart) {
        silenceStart = Date.now();
      } else if (Date.now() - silenceStart > SILENCE_DURATION) {
        // 3 sec silence → stop
        console.log("🔇 Auto-stopping (silence detected)");
        if (onSilenceCallback) onSilenceCallback();
        return;
      }
    }
    
    requestAnimationFrame(check);
  }
  check();
}

async function stopRecordingAndTranscribe() {
  return new Promise((resolve) => {
    if (!mediaRecorder || mediaRecorder.state === "inactive") {
      resolve("");
      return;
    }
    mediaRecorder.onstop = async () => {
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      const transcript = await sendToWhisper(blob);
      resolve(transcript);
    };
    mediaRecorder.stop();
  });
}

async function sendToWhisper(audioBlob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "answer.webm");

  try {
    const res = await fetch(
      "http://localhost:5001/api/interview/transcribe",
      { method: "POST", body: formData }
    );
    const data = await res.json();
    return data.transcript || "";
  } catch (err) {
    console.error("Transcribe failed:", err);
    return "";
  }
}