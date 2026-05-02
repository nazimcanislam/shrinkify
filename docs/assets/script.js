// ── OS detection ──────────────────────────────────────────────────────
function getOS() {
  // Prefer the modern userAgentData API (Chrome 90+, Edge 90+).
  // navigator.userAgent can be frozen/reduced in newer browsers, making
  // regex matching unreliable — userAgentData.platform is the canonical source.
  if (navigator.userAgentData && navigator.userAgentData.platform) {
    const p = navigator.userAgentData.platform;
    if (p === "Windows") return "Windows";
    if (p === "macOS") return "macOS";
    if (p === "Linux") return "Linux";
    if (p === "Android") return "Android";
    // iOS not exposed via userAgentData; fall through to legacy check
  }

  // Legacy fallback for Safari, Firefox, and older browsers
  const ua = navigator.userAgent || navigator.vendor || window.opera || "";
  const platform = navigator.platform || "";

  if (
    /iPad|iPhone|iPod/.test(ua) ||
    (platform === "MacIntel" && navigator.maxTouchPoints > 1)
  )
    return "iOS";
  if (/Macintosh|MacIntel|MacPPC|Mac68K/.test(ua)) return "macOS";
  if (/android/i.test(ua)) return "Android";
  if (/Win32|Win64|Windows|WinCE/.test(ua)) return "Windows";
  if (/Linux|X11/.test(ua)) return "Linux";
  return "unknown";
}

const os = getOS();
const detectedOsClassName = "detected-os";
if (os === "Windows")
  document.getElementById("dl-card-windows").classList.add(detectedOsClassName);
else if (os === "macOS")
  document.getElementById("dl-card-macos").classList.add(detectedOsClassName);
else if (os === "Linux")
  document.getElementById("dl-card-linux").classList.add(detectedOsClassName);
else if (os === "Android" || os === "iOS")
  document.getElementById("dl-card-mobile").classList.add(detectedOsClassName);

// ── Tabs ──────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach((b) => {
  b.addEventListener("click", () => {
    document
      .querySelectorAll(".tab-btn")
      .forEach((x) => x.classList.remove("active"));
    document
      .querySelectorAll(".tab-content")
      .forEach((x) => x.classList.remove("active"));
    b.classList.add("active");
    document.getElementById("tab-" + b.dataset.tab).classList.add("active");
  });
});
