const API = "http://localhost:5001/api";
const interviewId = sessionStorage.getItem("interview_id");
const candidateName = sessionStorage.getItem("candidate_name");
const jobTitle = sessionStorage.getItem("job_title");

let currentQuestions = [];
let currentQIndex = 0;
let timerInterval = null;
let timeLeft = 15 * 60;

if (!interviewId) {
  window.location.href = "index.html";
}

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("candidate-name").textContent = candidateName;
  document.getElementById("job-title").textContent = jobTitle;

  const stream = await navigator.mediaDevices.getUserMedia({
    video: true, audio: false
  });
  document.getElementById("camera-feed").srcObject = stream;

  await initMicrophone();
  await initAntiCheat(interviewId);

  document.getElementById("start-btn").addEventListener("click", startRound1);
  document.getElementById("next-round-btn").addEventListener("click", goToAptitude);
  
  // Hide manual buttons - now automatic
  document.getElementById("record-btn").style.display = "none";
  document.getElementById("done-btn").addEventListener("click", finishAnswering);
});

function startTimer(seconds) {
  timeLeft = seconds;
  updateTimer();
  timerInterval = setInterval(() => {
    timeLeft--;
    updateTimer();
    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      completeRound1();
    }
  }, 1000);
}

function updateTimer() {
  const m = Math.floor(timeLeft / 60);
  const s = timeLeft % 60;
  document.getElementById("timer").textContent = 
    `${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
}

function setStatus(icon, text, className = "") {
  document.getElementById("status-icon").textContent = icon;
  document.getElementById("status-text").textContent = text;
  document.getElementById("status-pill").className = "status-pill " + className;
}

async function startRound1() {
  document.getElementById("pre-start").classList.add("hidden");
  document.getElementById("qa-area").classList.remove("hidden");

  const res = await fetch(`${API}/interview/round1/start/${interviewId}`, {
    method: "POST"
  });
  const data = await res.json();

  currentQuestions = data.questions;
  document.getElementById("q-total").textContent = currentQuestions.length;
  
  startTimer(data.time_limit);
  askQuestion();
}

// ── Ask Question → Auto-record ─────────
function askQuestion() {
  if (currentQIndex >= currentQuestions.length) {
    completeRound1();
    return;
  }

  const question = currentQuestions[currentQIndex];
  document.getElementById("q-num").textContent = currentQIndex + 1;
  document.getElementById("question-box").textContent = question;
  document.getElementById("answer-text").textContent = "—";
  document.getElementById("done-btn").classList.add("hidden");

  setStatus("🔊", "AI is speaking...", "status-speaking");
  
  speak(question, () => {
    // Auto-start recording after AI finishes
    setTimeout(() => {
      autoStartRecording();
    }, 500);
  });
}

// ── Auto Start Recording ───────────────
function autoStartRecording() {
  setStatus("🎤", "Listening... (auto-stops after 3 sec silence)", "status-listening");
  document.getElementById("done-btn").classList.remove("hidden");
  
  startRecordingWithAutoStop(() => {
    // Auto-stop callback triggered by silence
    finishAnswering();
  });
}

// ── Finish Answering ───────────────────
async function finishAnswering() {
  // Prevent double-trigger
  if (document.getElementById("done-btn").classList.contains("hidden")) return;
  document.getElementById("done-btn").classList.add("hidden");
  
  setStatus("⏳", "Transcribing your answer...", "status-thinking");

  const transcript = await stopRecordingAndTranscribe();
  document.getElementById("answer-text").textContent = 
    transcript || "(no speech detected)";

  setStatus("🤖", "Evaluating...", "status-thinking");

  await fetch(`${API}/interview/round1/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interview_id: interviewId,
      question: currentQuestions[currentQIndex],
      answer: transcript
    })
  });

  currentQIndex++;
  setTimeout(askQuestion, 1500);
}

async function completeRound1() {
  clearInterval(timerInterval);
  speechSynthesis.cancel();
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }

  document.getElementById("qa-area").classList.add("hidden");
  document.getElementById("round-complete").classList.remove("hidden");

  const res = await fetch(`${API}/interview/round1/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interview_id: interviewId })
  });
  const data = await res.json();

  document.getElementById("round-score").textContent = 
    `Score: ${data.round1_score}% — Moving to Aptitude Round`;
  
  const checks = document.querySelectorAll(".sidebar .check-icon");
  checks[0].className = "check-icon pass";
  checks[0].textContent = "✓";
}

function goToAptitude() {
  window.location.href = "aptitude.html";
}