const API = "http://localhost:5001/api";
const interviewId = sessionStorage.getItem("interview_id");
const candidateName = sessionStorage.getItem("candidate_name");
const jobTitle = sessionStorage.getItem("job_title");

let questionCount = 0;
let timerInterval = null;
let timeLeft = 25 * 60;
let currentQuestion = "";

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

  document.getElementById("start-btn").addEventListener("click", startRound3);
  document.getElementById("done-btn").addEventListener("click", finishAnswering);
  document.getElementById("finish-btn").addEventListener("click", goToComplete);
});

// ── Timer ──────────────────────────────
function startTimer(seconds) {
  timeLeft = seconds;
  updateTimer();
  timerInterval = setInterval(() => {
    timeLeft--;
    updateTimer();
    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      completeRound3();
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

// ── Start Round 3 ──────────────────────
async function startRound3() {
  document.getElementById("pre-start").classList.add("hidden");
  document.getElementById("conversation-area").classList.remove("hidden");

  setStatus("⏳", "AI is preparing your first question...", "status-thinking");

  const res = await fetch(`${API}/interview/round3/start/${interviewId}`, {
    method: "POST"
  });
  const data = await res.json();

  startTimer(data.time_limit);
  askQuestion(data.question);
}

// ── Ask Question (AI speaks) ───────────
function askQuestion(question) {
  currentQuestion = question;
  questionCount++;
  
  document.getElementById("question-box").textContent = question;
  document.getElementById("answer-text").textContent = "—";
  document.getElementById("q-count").textContent = questionCount;
  document.getElementById("done-btn").classList.add("hidden");

  setStatus("🔊", "AI is speaking...", "status-speaking");
  
  speak(question, () => {
    setTimeout(() => {
      autoStartRecording();
    }, 500);
  });
}

// ── Auto-Start Recording ───────────────
function autoStartRecording() {
  setStatus("🎤", "Listening... (auto-stops after 3 sec silence)", "status-listening");
  document.getElementById("done-btn").classList.remove("hidden");
  
  startRecordingWithAutoStop(() => {
    finishAnswering();
  });
}

// ── Finish Answering → Get Next Question ──
async function finishAnswering() {
  if (document.getElementById("done-btn").classList.contains("hidden")) return;
  document.getElementById("done-btn").classList.add("hidden");
  
  setStatus("⏳", "Transcribing...", "status-thinking");

  const transcript = await stopRecordingAndTranscribe();
  document.getElementById("answer-text").textContent = 
    transcript || "(no speech detected)";

  setStatus("🤖", "AI is thinking of next question...", "status-thinking");

  const res = await fetch(`${API}/interview/round3/respond`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interview_id: interviewId,
      answer: transcript,
      question_count: questionCount
    })
  });
  const data = await res.json();

  if (data.done) {
    // AI ended the interview
    document.getElementById("question-box").textContent = data.message;
    speak(data.message, () => {
      setTimeout(completeRound3, 1500);
    });
  } else {
    // Next question
    setTimeout(() => askQuestion(data.question), 1000);
  }
}

// ── Complete Round 3 ───────────────────
async function completeRound3() {
  clearInterval(timerInterval);
  speechSynthesis.cancel();
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }

  document.getElementById("conversation-area").classList.add("hidden");
  document.getElementById("complete-area").classList.remove("hidden");

  await fetch(`${API}/interview/round3/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interview_id: interviewId })
  });

  // Hide score
  document.getElementById("round-score").textContent = 
    "Interview completed successfully. Your report will be reviewed by HR.";
  
  document.getElementById("r3-icon").className = "check-icon pass";
  document.getElementById("r3-icon").textContent = "✓";

  await fetch(`${API}/report/generate/${interviewId}`, {
    method: "POST"
  });

  document.getElementById("finish-btn").classList.remove("hidden");
}

function goToComplete() {
  window.location.href = "complete.html";
}