const API = "http://localhost:5001/api";
const interviewId = sessionStorage.getItem("interview_id");
const candidateName = sessionStorage.getItem("candidate_name");
const jobTitle = sessionStorage.getItem("job_title");

let sections = [];
let currentSectionIdx = 0;
let currentQuestionIdx = 0;
let answers = {};
let selectedOption = null;
let timerInterval = null;
let questionStartTime = null;
let timeLeft = 60;
let totalQuestions = 0;
let questionsAttempted = 0;

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

  await initAntiCheat(interviewId);

  document.getElementById("start-btn").addEventListener("click", startTest);
  document.getElementById("submit-btn").addEventListener("click", submitAnswer);
  document.getElementById("next-section-btn").addEventListener("click", startNextSection);
  document.getElementById("next-btn").addEventListener("click", goToRound3);
});

// ── Start Test ─────────────────────────
async function startTest() {
  document.getElementById("pre-start").classList.add("hidden");
  document.getElementById("section-intro").classList.remove("hidden");

  const res = await fetch(`${API}/aptitude/start/${interviewId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain: "general" })
  });
  const data = await res.json();

  console.log("DATA RECEIVED:", data);   // ADD THIS
  console.log("SECTIONS:", data.sections); // ADD THIS

  sections = data.sections;
  totalQuestions = data.total_questions;
  document.getElementById("q-total").textContent = totalQuestions;

  showSectionIntro();
}

// ── Section Intro ──────────────────────
function showSectionIntro() {
  const section = sections[currentSectionIdx];
  document.getElementById("section-num").textContent = currentSectionIdx + 1;
  document.getElementById("section-total").textContent = sections.length;
  document.getElementById("section-name").textContent = section.name + " Ability";
  document.getElementById("section-q-count").textContent = section.questions.length;
}

function startNextSection() {
  document.getElementById("section-intro").classList.add("hidden");
  document.getElementById("question-area").classList.remove("hidden");
  currentQuestionIdx = 0;
  showQuestion();
}

// ── Show Current Question ──────────────
function showQuestion() {
  const section = sections[currentSectionIdx];

  if (currentQuestionIdx >= section.questions.length) {
    // Section finished
    currentSectionIdx++;
    if (currentSectionIdx >= sections.length) {
      completeTest();
      return;
    }
    document.getElementById("question-area").classList.add("hidden");
    document.getElementById("section-intro").classList.remove("hidden");
    showSectionIntro();
    return;
  }

  const q = section.questions[currentQuestionIdx];
  selectedOption = null;

  document.getElementById("section-label").textContent = section.name;
  document.getElementById("current-q").textContent = currentQuestionIdx + 1;
  document.getElementById("section-q-total").textContent = section.questions.length;
  document.getElementById("q-num").textContent = questionsAttempted + 1;
  document.getElementById("question-text").textContent = q.question_text;
  document.getElementById("submit-btn").disabled = true;

  const progress = (questionsAttempted / totalQuestions) * 100;
  document.getElementById("progress-fill").style.width = `${progress}%`;

  const optionsList = document.getElementById("options-list");
  optionsList.innerHTML = "";

  q.options.forEach((opt, idx) => {
    const div = document.createElement("div");
    div.className = "mcq-option";
    div.dataset.key = opt.key;
    div.innerHTML = `
      <span class="mcq-letter">${String.fromCharCode(65 + idx)}</span>
      <span>${opt.text}</span>
    `;
    div.addEventListener("click", () => selectOption(div, opt.key));
    optionsList.appendChild(div);
  });

  questionStartTime = Date.now();
  startQuestionTimer();
}

// ── Select Option ──────────────────────
function selectOption(element, key) {
  document.querySelectorAll(".mcq-option").forEach(el => {
    el.classList.remove("selected");
  });
  element.classList.add("selected");
  selectedOption = key;
  document.getElementById("submit-btn").disabled = false;
}

// ── Timer ──────────────────────────────
function startQuestionTimer() {
  timeLeft = 60;
  updateTimerDisplay();

  timerInterval = setInterval(() => {
    timeLeft--;
    updateTimerDisplay();
    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      autoSubmit();
    }
  }, 1000);
}

function updateTimerDisplay() {
  const t = document.getElementById("timer");
  t.textContent = timeLeft;
  t.style.color = timeLeft <= 10 ? "var(--danger)" : "var(--accent)";
}

// ── Submit Answer ──────────────────────
function submitAnswer() {
  clearInterval(timerInterval);
  const q = sections[currentSectionIdx].questions[currentQuestionIdx];
  const timeTaken = Math.floor((Date.now() - questionStartTime) / 1000);

  answers[q.question_id] = {
    selected: selectedOption,
    time_taken: timeTaken
  };

  questionsAttempted++;
  currentQuestionIdx++;
  showQuestion();
}

// ── Auto Submit on Timeout ─────────────
function autoSubmit() {
  const q = sections[currentSectionIdx].questions[currentQuestionIdx];
  answers[q.question_id] = {
    selected: selectedOption || "",
    time_taken: 60
  };
  questionsAttempted++;
  currentQuestionIdx++;
  showQuestion();
}

// ── Complete Test ──────────────────────
async function completeTest() {
  clearInterval(timerInterval);
  document.getElementById("question-area").classList.add("hidden");
  document.getElementById("complete-area").classList.remove("hidden");

  const res = await fetch(`${API}/aptitude/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      interview_id: interviewId,
      answers: answers
    })
  });
  const data = await res.json();

  document.getElementById("score-text").textContent =
    `You scored ${data.round2_score}% — Moving to AI Interview`;

  document.getElementById("r2-icon").className = "check-icon pass";
  document.getElementById("r2-icon").textContent = "✓";
}

function goToRound3() {
  window.location.href = "round3.html";
}