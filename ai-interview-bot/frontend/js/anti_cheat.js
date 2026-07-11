let flagCount = 0;
let acInterviewId = null;
let detectionInterval = null;
let objectDetectionInterval = null;
let faceLandmarker = null;
let objectDetector = null;
const MAX_FLAGS = 3;

async function initAntiCheat(ivId) {
  acInterviewId = ivId;

  // Load existing flag count
  try {
    const res = await fetch(
      `http://localhost:5001/api/interview/flag-count/${ivId}`
    );
    const data = await res.json();
    flagCount = data.count || 0;
    document.getElementById("flag-count").textContent = flagCount;
  } catch (err) {
    console.log("Could not load flags");
  }

  // Tab switch detection
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      sendFlag("tab_switch", "Tab switched");
      showWarning("Do not switch tabs!");
    }
  });

  // Window blur
  window.addEventListener("blur", () => {
    sendFlag("window_blur", "Window lost focus");
  });

  // Disable right-click, copy, paste
  document.addEventListener("contextmenu", e => e.preventDefault());
  document.addEventListener("copy", e => e.preventDefault());
  document.addEventListener("paste", e => e.preventDefault());
  document.addEventListener("cut", e => e.preventDefault());

  // Block shortcuts
  document.addEventListener("keydown", (e) => {
    if (e.key === "F12" || 
       (e.ctrlKey && e.shiftKey && e.key === "I") ||
       (e.ctrlKey && e.key === "u")) {
      e.preventDefault();
    }
  });

  await initMediaPipe();
  await initObjectDetector();
  startDetectionLoop();
  
  console.log("✅ Enhanced anti-cheat active");
}

// ── Initialize MediaPipe Face Landmarker ──
async function initMediaPipe() {
  try {
    const { FilesetResolver, FaceLandmarker } = window;
    
    const vision = await FilesetResolver.forVisionTasks(
      "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.6/wasm"
    );
    
    faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
        delegate: "GPU"
      },
      outputFaceBlendshapes: true,
      runningMode: "VIDEO",
      numFaces: 2
    });
    
    console.log("MediaPipe loaded");
  } catch (e) {
    console.error("MediaPipe load failed:", e);
  }
}

// ── Initialize Object Detector ──
async function initObjectDetector() {
  try {
    objectDetector = await cocoSsd.load();
    console.log("Object detector loaded");
  } catch (e) {
    console.error("Object detector load failed:", e);
  }
}

// ── Main Detection Loop ──
function startDetectionLoop() {
  const video = document.getElementById("camera-feed");
  const canvas = document.getElementById("detection-overlay");
  
  let noFaceCount = 0;
  let multiFaceCount = 0;
  let lookAwayCount = 0;
  let lastVideoTime = -1;

  // Face detection - every 1 sec
  detectionInterval = setInterval(() => {
    if (!faceLandmarker || video.readyState < 2) return;
    
    // Match canvas size to video DISPLAY size, not source size
    const rect = video.getBoundingClientRect();
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.style.width = rect.width + "px";
    canvas.style.height = rect.height + "px";

    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (lastVideoTime === video.currentTime) return;
    lastVideoTime = video.currentTime;

    const results = faceLandmarker.detectForVideo(video, performance.now());
    const indicator = document.getElementById("gaze-indicator");
    const gazeText = document.getElementById("gaze-text");

    if (!results.faceLandmarks || results.faceLandmarks.length === 0) {
      if (indicator) {
        indicator.className = "gaze-indicator bad";
        gazeText.textContent = "No face";
      }
      noFaceCount++;
      if (noFaceCount >= 4) {
        sendFlag("no_face", "Face not visible");
        showWarning("Please face the camera");
        noFaceCount = 0;
      }
      return;
    }
    noFaceCount = 0;

    if (results.faceLandmarks.length > 1) {
      if (indicator) {
        indicator.className = "gaze-indicator bad";
        gazeText.textContent = "Multiple faces!";
      }
      multiFaceCount++;
      if (multiFaceCount >= 4) {
        sendFlag("multiple_faces", `${results.faceLandmarks.length} faces`);
        showWarning("Multiple people detected!");
        multiFaceCount = 0;
      }
      return;
    }
    multiFaceCount = 0;

    const landmarks = results.faceLandmarks[0];
    drawFaceMesh(ctx, landmarks, canvas.width, canvas.height);
    
    const gazeStatus = analyzeGaze(landmarks, results.faceBlendshapes);
    
    if (gazeStatus.lookingAway) {
      if (indicator) {
        indicator.className = "gaze-indicator bad";
        gazeText.textContent = gazeStatus.reason;
      }
      lookAwayCount++;
      if (lookAwayCount >= 4) {
        sendFlag("looking_away", gazeStatus.reason);
        showWarning("Please look at the screen");
        lookAwayCount = 0;
      }
    } else {
      if (indicator) {
        indicator.className = "gaze-indicator good";
        gazeText.textContent = "Focused";
      }
      lookAwayCount = 0;
    }
  }, 1000);

  // Object detection - every 3 sec
  objectDetectionInterval = setInterval(async () => {
    if (!objectDetector || video.readyState < 2) return;
    
    try {
      const predictions = await objectDetector.detect(video);
      checkSuspiciousObjects(predictions);
    } catch (e) {
      console.error("Object detection error:", e);
    }
  }, 2000);
}

// ── Draw Face Mesh Overlay ──
function drawFaceMesh(ctx, landmarks, w, h) {
  // Face bounding box
  let minX = w, minY = h, maxX = 0, maxY = 0;
  landmarks.forEach(p => {
    const x = p.x * w;
    const y = p.y * h;
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  });
  
  ctx.strokeStyle = "#3b82f6";
  ctx.lineWidth = 2;
  ctx.strokeRect(minX, minY, maxX - minX, maxY - minY);

  // Draw all 468 mesh dots (small)
  ctx.fillStyle = "rgba(34, 197, 94, 0.5)";
  landmarks.forEach(p => {
    ctx.beginPath();
    ctx.arc(p.x * w, p.y * h, 1, 0, 2 * Math.PI);
    ctx.fill();
  });

  // Left iris (landmark 468-472) - YELLOW circle
  if (landmarks[468]) {
    const iris = landmarks[468];
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(iris.x * w, iris.y * h, 12, 0, 2 * Math.PI);
    ctx.stroke();
  }
  
  // Right iris (landmark 473)
  if (landmarks[473]) {
    const iris = landmarks[473];
    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(iris.x * w, iris.y * h, 12, 0, 2 * Math.PI);
    ctx.stroke();
  }

  // Head direction line (nose tip)
  if (landmarks[1]) {
    const nose = landmarks[1];
    const center = landmarks[168];
    if (center) {
      ctx.strokeStyle = "#ef4444";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(center.x * w, center.y * h);
      ctx.lineTo(nose.x * w, nose.y * h);
      ctx.stroke();
    }
  }
}

// ── Analyze Gaze Direction ──
function analyzeGaze(landmarks, blendshapes) {
  // Use face blendshapes for accurate gaze
  if (blendshapes && blendshapes.length > 0) {
    const shapes = blendshapes[0].categories;
    const lookLeft = shapes.find(s => s.categoryName === "eyeLookOutLeft")?.score || 0;
    const lookRight = shapes.find(s => s.categoryName === "eyeLookOutRight")?.score || 0;
    const lookUp = shapes.find(s => s.categoryName === "eyeLookUpLeft")?.score || 0;
    const lookDown = shapes.find(s => s.categoryName === "eyeLookDownLeft")?.score || 0;
    const eyeClose = shapes.find(s => s.categoryName === "eyeBlinkLeft")?.score || 0;

    if (eyeClose > 0.85) {
      return { lookingAway: true, reason: "Eyes closed" };
    }
    if (lookLeft > 0.7) {
      return { lookingAway: true, reason: "Looking left" };
    }
    if (lookRight > 0.7) {
      return { lookingAway: true, reason: "Looking right" };
    }
    if (lookDown > 0.7) {
      return { lookingAway: true, reason: "Looking down" };
    }
    if (lookUp > 0.7) {
      return { lookingAway: true, reason: "Looking up" };
    }
  }

  // Fallback: head pose using landmarks
  const noseTip = landmarks[1];
  const leftEye = landmarks[33];
  const rightEye = landmarks[263];
  const chin = landmarks[152];
  const forehead = landmarks[10];

  const eyeCenter = {
    x: (leftEye.x + rightEye.x) / 2,
    y: (leftEye.y + rightEye.y) / 2
  };

  const noseOffsetX = Math.abs(noseTip.x - eyeCenter.x);
  const eyeDistance = Math.abs(leftEye.x - rightEye.x);
  const turnRatio = noseOffsetX / eyeDistance;

  const verticalRatio = (noseTip.y - eyeCenter.y) / (chin.y - eyeCenter.y);

  if (turnRatio > 0.5) {
    return { lookingAway: true, reason: "Head turned" };
  }
  if (verticalRatio > 0.85) {
    return { lookingAway: true, reason: "Looking down" };
  }
  if (verticalRatio < 0.15) {
    return { lookingAway: true, reason: "Looking up" };
  }

  return { lookingAway: false, reason: "Focused" };
}

// ── Check Suspicious Objects ──
function checkSuspiciousObjects(predictions) {
  const suspiciousObjects = [
    "cell phone", "book", "laptop", "remote", 
    "keyboard", "tv", "tablet"
  ];

  for (const pred of predictions) {
    if (suspiciousObjects.includes(pred.class) && pred.score > 0.6) {
      sendFlag("suspicious_object", `${pred.class} detected`);
      showWarning(`${pred.class} detected in frame!`);
      return;
    }
  }
}

// ── Send Flag to Backend ──
async function sendFlag(flagType, detail) {
  try {
    const res = await fetch(
      "http://localhost:5001/api/interview/flag",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interview_id: acInterviewId,
          flag_type: flagType,
          detail: detail
        })
      }
    );
    const data = await res.json();
    flagCount = data.count || flagCount + 1;
    document.getElementById("flag-count").textContent = flagCount;

    if (data.action === "terminate") {
      terminateInterview();
    }
  } catch (err) {
    console.error("Flag error:", err);
  }
}

function showWarning(msg) {
  const banner = document.getElementById("warning-banner");
  banner.textContent = msg;
  banner.classList.remove("hidden");
  setTimeout(() => banner.classList.add("hidden"), 4000);
}

function terminateInterview() {
  if (detectionInterval) clearInterval(detectionInterval);
  if (objectDetectionInterval) clearInterval(objectDetectionInterval);
  document.body.innerHTML = `
    <div style="text-align:center; padding:60px; color:#fff; background:#0a0e27; min-height:100vh;">
      <div style="font-size:64px;">🚫</div>
      <h1 style="color:#ef4444;">Interview Terminated</h1>
      <p style="margin-top:16px;">Too many violations detected.</p>
      <p style="margin-top:8px; color:#8b94b3;">
        Your session has been flagged for HR review.
      </p>
    </div>
  `;
}