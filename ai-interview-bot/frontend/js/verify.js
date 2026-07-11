const API = "http://localhost:5001/api";
const interviewId = sessionStorage.getItem("interview_id");

let idFile = null;
let liveBlob = null;
let videoStream = null;
let docValidated = false;

if (!interviewId) {
  alert("Session expired. Please restart.");
  window.location.href = "index.html";
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("id-file").addEventListener("change", previewId);
  document.getElementById("validate-id-btn").addEventListener("click", validateDocument);
  document.getElementById("proceed-camera-btn").addEventListener("click", goToCamera);
  document.getElementById("reupload-btn").addEventListener("click", () => location.reload());
  document.getElementById("capture-btn").addEventListener("click", captureFace);
  document.getElementById("verify-btn").addEventListener("click", verifyFace);
  
  const retakeBtn = document.getElementById("retake-btn");
  if (retakeBtn) {
    retakeBtn.addEventListener("click", () => {
      autoCaptured = false;
      alignedCount = 0;
      liveBlob = null;
      document.getElementById("captured-preview").classList.add("hidden");
      document.getElementById("verify-btn").classList.add("hidden");
      document.getElementById("retake-btn").classList.add("hidden");
      document.getElementById("capture-btn").classList.remove("hidden");
      startFaceDetection();
    });
  }
});

function previewId(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    alert("File too large (max 5MB)");
    return;
  }
  idFile = file;
  
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById("id-img").src = e.target.result;
    document.getElementById("id-preview").classList.remove("hidden");
  };
  reader.readAsDataURL(file);
}

// ── STEP 1+2: Validate Document ──
async function validateDocument() {
  if (!idFile) {
    alert("Please upload ID");
    return;
  }

  document.getElementById("step-upload").classList.add("hidden");
  document.getElementById("step-verifying").classList.remove("hidden");
  document.getElementById("verifying-text").textContent = "Validating document...";

  const formData = new FormData();
  formData.append("id_photo", idFile);

  try {
    const res = await fetch(
      `${API}/verify/document/${interviewId}`,
      { method: "POST", body: formData }
    );
    const data = await res.json();
    
    document.getElementById("step-verifying").classList.add("hidden");
    showValidationResult(data);
  } catch (err) {
    document.getElementById("step-verifying").classList.add("hidden");
    showValidationResult({ valid: false, error: err.message });
  }
}

function showValidationResult(data) {
  document.getElementById("step-validation").classList.remove("hidden");
  document.getElementById("step1").className = data.valid ? "badge badge-success" : "badge badge-danger";
  
  const result = document.getElementById("validation-result");
  
  if (!data.valid) {
    result.innerHTML = `
      <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.3); padding:16px; border-radius:10px; margin:16px 0;">
        <p style="color:var(--danger); font-weight:600;">❌ ${data.error}</p>
      </div>
    `;
    document.getElementById("reupload-btn").classList.remove("hidden");
    return;
  }

  const nameCheck = data.name_check || {};
  const nameMatched = nameCheck.match;
  
  document.getElementById("step2").className = nameMatched ? "badge badge-success" : "badge badge-warning";
  
  result.innerHTML = `
    <div style="background:rgba(34,197,94,0.1); border:1px solid rgba(34,197,94,0.3); padding:16px; border-radius:10px; margin:16px 0;">
      <p style="color:var(--success); font-weight:600;">✅ Document Validated</p>
      <p style="margin-top:8px;">Type: <strong>${data.doc_type}</strong></p>
    </div>
    
    <div style="background:${nameMatched ? 'rgba(34,197,94,0.1)' : 'rgba(245,158,11,0.1)'}; border:1px solid ${nameMatched ? 'rgba(34,197,94,0.3)' : 'rgba(245,158,11,0.3)'}; padding:16px; border-radius:10px; margin:16px 0;">
      <p style="color:${nameMatched ? 'var(--success)' : 'var(--warning)'}; font-weight:600;">
        ${nameMatched ? '✅' : '⚠️'} Name Match: ${nameCheck.score}%
      </p>
      ${nameCheck.id_name ? `<p style="margin-top:8px; font-size:13px;">ID Name: <strong>${nameCheck.id_name}</strong></p>` : ''}
      ${nameCheck.resume_name ? `<p style="font-size:13px;">Resume Name: <strong>${nameCheck.resume_name}</strong></p>` : ''}
      ${!nameMatched ? '<p style="margin-top:8px; font-size:12px; color:var(--text-dim);">Name partially matched. Face verification required to proceed.</p>' : ''}
    </div>
  `;

  document.getElementById("proceed-camera-btn").classList.remove("hidden");
}

// ── STEP 3: Camera ──
let faceDetectInterval = null;
let alignedCount = 0;
let autoCaptured = false;

async function goToCamera() {
  document.getElementById("step-validation").classList.add("hidden");
  document.getElementById("step-camera").classList.remove("hidden");
  document.getElementById("step3").className = "badge badge-info";

  try {
    videoStream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
      audio: false
    });
    document.getElementById("video").srcObject = videoStream;
    
    document.getElementById("video").onloadedmetadata = () => {
      startFaceDetection();
    };
  } catch (err) {
    alert("Camera access denied");
  }
}

async function startFaceDetection() {
  if (typeof faceapi === 'undefined') return;

  await faceapi.nets.tinyFaceDetector.loadFromUri("models");

  const video = document.getElementById("video");
  const guide = document.getElementById("face-guide");
  const status = document.getElementById("face-status");

  faceDetectInterval = setInterval(async () => {
    if (autoCaptured) return;

    const detection = await faceapi.detectSingleFace(
      video,
      new faceapi.TinyFaceDetectorOptions({ inputSize: 224 })
    );

    if (!detection) {
      guide.className = "face-guide";
      status.textContent = "No face detected";
      alignedCount = 0;
      return;
    }

    const box = detection.box;
    const videoW = video.videoWidth;
    const videoH = video.videoHeight;
    
    const centerX = box.x + box.width/2;
    const centerY = box.y + box.height/2;
    const offsetX = Math.abs(centerX - videoW/2);
    const offsetY = Math.abs(centerY - videoH/2);
    const sizeOk = box.width > videoW * 0.25 && box.width < videoW * 0.6;
    const positionOk = offsetX < videoW * 0.15 && offsetY < videoH * 0.15;

    if (sizeOk && positionOk) {
      guide.className = "face-guide aligned";
      alignedCount++;
      status.textContent = `Hold still... ${alignedCount}/15`;
      
      if (alignedCount >= 15) {
        autoCaptured = true;
        clearInterval(faceDetectInterval);
        status.textContent = "✅ Captured!";
        captureFace();
      }
    } else {
      alignedCount = 0;
      guide.className = "face-guide warning";
      
      if (!sizeOk) {
        status.textContent = box.width < videoW * 0.25 ? "Move closer" : "Move back";
      } else {
        status.textContent = "Center your face";
      }
    }
  }, 100);
}

function captureFace() {
  const video = document.getElementById("video");
  const canvas = document.getElementById("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);

  canvas.toBlob((blob) => {
    liveBlob = blob;
    const url = URL.createObjectURL(blob);
    document.getElementById("captured-img").src = url;
    document.getElementById("captured-preview").classList.remove("hidden");
    document.getElementById("capture-btn").classList.add("hidden");
    document.getElementById("verify-btn").classList.remove("hidden");
    document.getElementById("retake-btn").classList.remove("hidden");
    
    if (faceDetectInterval) clearInterval(faceDetectInterval);
  }, "image/jpeg", 0.95);
}

async function verifyFace() {
  if (!liveBlob) {
    alert("Please capture your face first");
    return;
  }

  document.getElementById("step-camera").classList.add("hidden");
  document.getElementById("step-verifying").classList.remove("hidden");
  document.getElementById("verifying-text").textContent = "Matching face with ID...";

  const formData = new FormData();
  formData.append("live_photo", liveBlob, "live.jpg");

  try {
    const res = await fetch(
      `${API}/verify/face/${interviewId}`,
      { method: "POST", body: formData }
    );
    const data = await res.json();

    if (videoStream) {
      videoStream.getTracks().forEach(t => t.stop());
    }
    
    document.getElementById("step-verifying").classList.add("hidden");
    showFinalResult(data);
  } catch (err) {
    document.getElementById("step-verifying").classList.add("hidden");
    showFinalResult({ verified: false, error: err.message });
  }
}

function showFinalResult(data) {
  document.getElementById("step-result").classList.remove("hidden");
  document.getElementById("step3").className = data.verified ? "badge badge-success" : "badge badge-danger";

  const content = document.getElementById("result-content");

  if (data.verified) {
    content.innerHTML = `
      <div style="font-size:64px; margin-bottom:16px;">✅</div>
      <h2 style="color:var(--success);">Identity Verified!</h2>
      <p class="subtitle">Face match confidence: ${data.confidence}%</p>
      <button type="button" class="btn" id="start-btn">Start Round 1 →</button>
    `;
    document.getElementById("start-btn").addEventListener("click", () => {
      window.location.href = "interview.html";
    });
  } else {
    content.innerHTML = `
      <div style="font-size:64px; margin-bottom:16px;">❌</div>
      <h2 style="color:var(--danger);">Verification Failed</h2>
      <p class="subtitle">${data.error || "Face did not match ID photo"}</p>
      <p style="font-size:13px; color:var(--text-dim); margin-top:8px;">
        Make sure good lighting and clear face visibility
      </p>
      <button type="button" class="btn" id="retry-btn">Try Again</button>
    `;
    document.getElementById("retry-btn").addEventListener("click", () => {
      location.reload();
    });
  }
}