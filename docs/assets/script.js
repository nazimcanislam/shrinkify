// ── i18n ──────────────────────────────────────────────────────────────
const translations = {
  en: {
    page_title: "Shrinkify — Make Your Media Library Breathe Again",
    nav_how: "How it works",
    nav_guide: "Guide",
    nav_download: "↓ Download",
    hero_badge: "Free & Open Source",
    hero_h1: "Make your media library <em>breathe again.</em>",
    hero_p:
      "Shrinkify converts old H.264 videos and JPEG photos to modern H.265 and HEIF formats — cutting your library size by up to 60% without losing a single pixel of quality.",
    hero_btn_download: "↓ Download free",
    hero_btn_github: "View on GitHub",
    ticker_label: "Live Example",
    ticker_total: "Total result",
    stat_video: "average reduction on H.264 video",
    stat_photo: "average reduction on JPEG photos",
    stat_platforms: "platforms — Windows, macOS, Linux",
    how_label: "How it works",
    how_h3: "Three steps. Zero quality loss.",
    how_p:
      "does the technical heavy lifting so you don't have to know what H.265 means.",
    step1_num: "01 — SELECT",
    step1_h3: "Point it at a folder",
    step1_p:
      "Drop in your Google Takeout export, camera roll backup, or any folder full of photos and videos.",
    step2_num: "02 — ANALYZE",
    step2_h3: "Let it scan",
    step2_p:
      "reads every file's codec, bitrate, and format. Finds duplicates. Shows a detailed savings report before touching anything.",
    step3_num: "03 — SHRINK",
    step3_h3: "One click to convert",
    step3_p:
      "Converted files land in a <code>shrinkified/</code> folder. Originals are untouched. If a conversion makes a file bigger, it's discarded.",
    feat_label: "Features",
    feat_h3: "Everything your media library needs.",
    feat_p: "Built for everyday people and power users alike.",
    feat1_h3: "H.264 → H.265 video conversion",
    feat1_p:
      "Re-encodes old MP4, MOV, AVI, and MKV files to HEVC — the same quality, half the size. Uses your GPU automatically on Apple Silicon, NVIDIA, Intel, and AMD hardware.",
    feat1_badge: "Up to 60% smaller",
    feat2_h3: "JPEG → HEIF conversion",
    feat2_p:
      "Converts JPEG photos to the modern HEIF format, the same format iPhones and recent Androids shoot in natively. EXIF metadata, GPS location, and date are fully preserved.",
    feat2_badge: "Up to 40% smaller",
    feat3_h3: "Duplicate file detection",
    feat3_p:
      "Finds files that are identical regardless of filename using fast file hashing. Shows you exactly which files are duplicates and lets you delete them safely.",
    feat4_h3: "Beautiful HTML report",
    feat4_p_pre: "After every scan,",
    feat4_p_post:
      "generates a detailed report showing codec distribution, estimated savings breakdown, and a list of every file — organized into categories.",
    feat5_h3: "Folder structure preserved",
    feat5_p:
      'Enable "Preserve folder structure" and your subfolder hierarchy is mirrored inside the output folder. Your album organization stays intact.',
    feat6_h3: "Originals are never touched",
    feat6_p:
      "Every converted file goes into a <code>shrinkified/</code> subfolder. Your source files are read-only. Dry run mode lets you preview results before committing.",
    results_label: "Real results",
    results_h3: "See the difference.",
    results_p: "Actual results from a real Google Takeout export.",
    results_before: "Before",
    results_after: "After Shrinkify",
    results_total_label: "Total saved in this example",
    dl_label: "Download",
    dl_h3: "Free on every platform.",
    dl_p: "Download the right version for your operating system. All builds are produced automatically by GitHub Actions.",
    dl_badge_tested: "Tested ✓",
    dl_win_p: "Windows 10 or later. Installer-free — just download and run.",
    dl_win_btn: "↓ Download .exe",
    dl_mac_p:
      "macOS 12 or later. Apple Silicon native. GPU acceleration via VideoToolbox.",
    dl_mac_btn: "↓ Download .zip",
    dl_linux_p:
      "Ubuntu 22.04+. Run the binary directly. May require <code>chmod +x Shrinkify</code>.",
    dl_linux_btn: "↓ Download binary",
    dl_mobile_badge: "Possible future release",
    dl_mobile_p:
      "Mobile support is not currently available. We may explore iOS and Android builds in a future release as the project matures.",
    dl_mobile_btn: "Not available yet",
    dl_note:
      '<strong>⚠ Requires ffmpeg</strong> — Shrinkify uses ffmpeg for video analysis and conversion. Install it from <a href="https://ffmpeg.org/download.html" target="_blank">ffmpeg.org</a> and make sure it\'s in your system PATH. On macOS: <code>brew install ffmpeg</code>. On Linux: <code>sudo apt install ffmpeg</code>.',
    guide_label: "Quick start guide",
    guide_h3: "Up and running in minutes.",
    guide_p: "Scan according to your requirements.",
    guide_folder_mode: "Folder Mode",
    guide_single_mode: "Single File Mode",
    guide_tab_folder: "🗂️ Folder Mode",
    guide_tab_single: "📄 Single File Mode",
    guide_f1_h3: 'Open Shrinkify and choose "Folder"',
    guide_f1_p:
      "The welcome screen lets you choose between a single file or an entire folder.",
    guide_f2_h3: "Select your folder and click Analyze",
    guide_f2_p:
      "Shrinkify scans every file, finds duplicates, and shows an estimated savings report.",
    guide_f3_h3: "Try Dry Run first",
    guide_f3_p:
      'Check "Dry run" to preview what would happen without touching any files.',
    guide_f4_h3: "Click Convert Files",
    guide_f4_p:
      "Converted files appear in a <code>shrinkified/</code> subfolder. Originals untouched.",
    guide_s1_h3: 'Open Shrinkify and choose "Single File"',
    guide_s1_p:
      "Perfect for converting one video or photo without scanning a whole folder.",
    guide_s2_h3: "Browse to your file",
    guide_s2_p: "Supports MP4, MOV, AVI, MKV, JPG, HEIC, WEBP, and more. PNG files are scanned but not converted (lossless format).",
    guide_s3_h3: "Choose a quality preset",
    guide_s3_p:
      "Balanced is the recommended default. Maximum Shrink gives the smallest file. Conservative is safest for archival.",
    guide_s4_h3: "Analyze then Convert",
    guide_s4_p:
      "The converted file lands next to the original in a <code>shrinkified/</code> folder.",
    compat_label: "Compatibility",
    compat_h3: "Will the converted files open on my devices?",
    compat_p:
      "H.265 and HEIF are modern standards supported on all devices <strong>from roughly 2018</strong> onwards. Here's a quick reference before you convert your whole library.",
    compat_p_strong: "from roughly 2018",
    compat_good_h4: "✅ Well supported",
    compat_good_1:
      'Windows 10 / 11 <span style="color: var(--muted)">(free HEVC extension from Microsoft Store)</span>',
    compat_good_2: "macOS High Sierra (10.13) and later",
    compat_good_3: "iPhone / iPad — iOS 11 and later",
    compat_good_4: "Android 9 and later",
    compat_good_5: "Smart TVs from 2018 onwards",
    compat_good_6: "VLC on any platform",
    compat_bad_h4: "⚠️ May have issues",
    compat_bad_1: "Windows 7 / 8 — no native H.265 or HEIF support",
    compat_bad_2: "Android 8 and older — inconsistent hardware support",
    compat_bad_3: "Smart TVs older than 2018",
    compat_bad_4: "Old digital photo frames",
    compat_footer:
      "If you share files with people on older devices, keep your originals. Shrinkify <strong>never deletes them</strong>.",
    footer_desc:
      "Analyze media files, suggest codec conversions, detect duplicates, and generate a detailed HTML report. Free and open source, forever.",
    footer_github: "GitHub",
    footer_releases: "Releases",
    footer_bug: "Report a bug",
    footer_made_by:
      'Made by <a href="https://github.com/nazimcanislam" target="_blank">Nazımcan İslam</a>',
    footer_collab:
      '🤝 Built in collaboration with <a href="https://claude.ai" target="_blank">Claude</a> (Anthropic)',
  },
  tr: {
    page_title: "Shrinkify — Medya Kütüphanenize Nefes Aldırın",
    nav_how: "Nasıl çalışır",
    nav_guide: "Rehber",
    nav_download: "↓ İndir",
    hero_badge: "Ücretsiz & Açık Kaynak",
    hero_h1: "Medya kütüphanenize <em>nefes aldırın.</em>",
    hero_p:
      "Shrinkify, eski H.264 videolarınızı ve JPEG fotoğraflarınızı modern H.265 ve HEIF formatlarına dönüştürür — tek bir piksel kalite kaybı olmadan kütüphane boyutunuzu %60'a kadar küçültür.",
    hero_btn_download: "↓ Ücretsiz indir",
    hero_btn_github: "GitHub'da görüntüle",
    ticker_label: "Canlı Örnek",
    ticker_total: "Toplam sonuç",
    stat_video: "H.264 videolarda ortalama küçülme",
    stat_photo: "JPEG fotoğraflarda ortalama küçülme",
    stat_platforms: "platform — Windows, macOS, Linux",
    how_label: "Nasıl çalışır",
    how_h3: "Üç adım. Sıfır kalite kaybı.",
    how_p:
      "teknik ağır işleri sizin adınıza yapar; H.265'in ne olduğunu bilmenize gerek kalmaz.",
    step1_num: "01 — SEÇ",
    step1_h3: "Bir klasöre yönlendirin",
    step1_p:
      "Google Takeout dışa aktarmanızı, kamera yedeklerinizi veya fotoğraf ve videolarla dolu herhangi bir klasörü ekleyin.",
    step2_num: "02 — ANALİZ ET",
    step2_h3: "Taramasını bekleyin",
    step2_p:
      "her dosyanın codec'ini, bit hızını ve formatını okur. Kopyaları bulur. Herhangi bir dosyaya dokunmadan önce ayrıntılı bir tasarruf raporu gösterir.",
    step3_num: "03 — KÜÇÜLT",
    step3_h3: "Tek tıkla dönüştürün",
    step3_p:
      "Dönüştürülen dosyalar <code>shrinkified/</code> klasörüne kaydedilir. Orijinaller dokunulmadan kalır. Bir dönüşüm dosyayı büyütürse otomatik olarak iptal edilir.",
    feat_label: "Özellikler",
    feat_h3: "Medya kütüphanenizin ihtiyacı olan her şey.",
    feat_p: "Günlük kullanıcılar ve ileri düzey kullanıcılar için tasarlandı.",
    feat1_h3: "H.264 → H.265 video dönüşümü",
    feat1_p:
      "Eski MP4, MOV, AVI ve MKV dosyalarını HEVC'ye yeniden kodlar — aynı kalite, yarı boyut. Apple Silicon, NVIDIA, Intel ve AMD donanımlarında GPU'yu otomatik olarak kullanır.",
    feat1_badge: "%60'a kadar daha küçük",
    feat2_h3: "JPEG → HEIF dönüşümü",
    feat2_p:
      "JPEG fotoğrafları modern HEIF formatına dönüştürür; iPhone'ların ve yeni Android cihazların doğal olarak kullandığı format. EXIF meta verileri, GPS konumu ve tarih eksiksiz korunur.",
    feat2_badge: "%40'a kadar daha küçük",
    feat3_h3: "Yinelenen dosya tespiti",
    feat3_p:
      "Dosya adından bağımsız olarak hızlı dosya karma yöntemiyle aynı dosyaları bulur. Hangi dosyaların kopya olduğunu tam olarak gösterir ve güvenle silmenizi sağlar.",
    feat4_h3: "Güzel HTML raporu",
    feat4_p_pre: "Her taramadan sonra",
    feat4_p_post:
      "codec dağılımını, tahmini tasarruf dökümünü ve kategorilere ayrılmış her dosyanın listesini içeren ayrıntılı bir rapor oluşturur.",
    feat5_h3: "Klasör yapısı korunur",
    feat5_p:
      '"Klasör yapısını koru" seçeneğini etkinleştirdiğinizde alt klasör hiyerarşiniz çıktı klasöründe de yansıtılır. Albüm düzeniniz bozulmaz.',
    feat6_h3: "Orijinaller asla dokunulmaz",
    feat6_p:
      "Dönüştürülen her dosya <code>shrinkified/</code> alt klasörüne kaydedilir. Kaynak dosyalarınız salt okunurdur. Kuru çalıştırma modu, değişiklikleri kaydetmeden önce sonuçları önizlemenizi sağlar.",
    results_label: "Gerçek sonuçlar",
    results_h3: "Farkı görün.",
    results_p:
      "Gerçek bir Google Takeout dışa aktarmasından elde edilen sonuçlar.",
    results_before: "Önce",
    results_after: "Shrinkify Sonrası",
    results_total_label: "Bu örnekte toplam kazanım",
    dl_label: "İndir",
    dl_h3: "Her platformda ücretsiz.",
    dl_p: "İşletim sisteminize uygun sürümü indirin. Tüm derlemeler GitHub Actions tarafından otomatik olarak üretilir.",
    dl_badge_tested: "Test edildi ✓",
    dl_win_p:
      "Windows 10 veya üzeri. Kurulum gerektirmez — sadece indirip çalıştırın.",
    dl_win_btn: "↓ .exe indir",
    dl_mac_p:
      "macOS 12 veya üzeri. Apple Silicon için optimize edildi. VideoToolbox ile GPU hızlandırma.",
    dl_mac_btn: "↓ .zip indir",
    dl_linux_p:
      "Ubuntu 22.04+. İkili dosyayı doğrudan çalıştırın. <code>chmod +x Shrinkify</code> gerekebilir.",
    dl_linux_btn: "↓ İkili dosyayı indir",
    dl_mobile_badge: "Olası gelecek sürüm",
    dl_mobile_p:
      "Mobil destek şu anda mevcut değil. Proje olgunlaştıkça gelecek bir sürümde iOS ve Android desteği eklenebilir.",
    dl_mobile_btn: "Henüz mevcut değil",
    dl_note:
      '<strong>⚠ ffmpeg gereklidir</strong> — Shrinkify, video analizi ve dönüşümü için ffmpeg kullanır. <a href="https://ffmpeg.org/download.html" target="_blank">ffmpeg.org</a> adresinden yükleyin ve sistem PATH\'inizde olduğundan emin olun. macOS\'ta: <code>brew install ffmpeg</code>. Linux\'ta: <code>sudo apt install ffmpeg</code>.',
    guide_label: "Hızlı başlangıç rehberi",
    guide_h3: "Dakikalar içinde hazır.",
    guide_p: "İhtiyacınıza göre tarama yapın.",
    guide_folder_mode: "Klasör Modu",
    guide_single_mode: "Tek Dosya Modu",
    guide_tab_folder: "🗂️ Klasör Modu",
    guide_tab_single: "📄 Tek Dosya Modu",
    guide_f1_h3: 'Shrinkify\'ı açın ve "Klasör" seçeneğini seçin',
    guide_f1_p:
      "Karşılama ekranı, tek dosya veya tüm klasör arasında seçim yapmanızı sağlar.",
    guide_f2_h3: "Klasörünüzü seçin ve Analiz Et'e tıklayın",
    guide_f2_p:
      "Shrinkify her dosyayı tarar, kopyaları bulur ve tahmini tasarruf raporu gösterir.",
    guide_f3_h3: "Önce Kuru Çalıştırma'yı deneyin",
    guide_f3_p:
      '"Kuru çalıştırma" seçeneğini işaretleyerek hiçbir dosyaya dokunmadan ne olacağını önizleyin.',
    guide_f4_h3: "Dosyaları Dönüştür'e tıklayın",
    guide_f4_p:
      "Dönüştürülen dosyalar <code>shrinkified/</code> alt klasöründe görünür. Orijinaller dokunulmaz.",
    guide_s1_h3: 'Shrinkify\'ı açın ve "Tek Dosya" seçeneğini seçin',
    guide_s1_p:
      "Tüm klasörü taramadan tek bir video veya fotoğrafı dönüştürmek için idealdir.",
    guide_s2_h3: "Dosyanıza gidin",
    guide_s2_p:
      "MP4, MOV, AVI, MKV, JPG, HEIC, WEBP ve daha fazlasını destekler. PNG dosyaları taranır ancak dönüştürülmez (kayıpsız format).",
    guide_s3_h3: "Bir kalite önayarı seçin",
    guide_s3_p:
      "Dengeli, önerilen varsayılandır. Maksimum Küçültme en küçük dosyayı verir. Muhafazakâr arşivleme için en güvenlidir.",
    guide_s4_h3: "Analiz Et, ardından Dönüştür",
    guide_s4_p:
      "Dönüştürülen dosya, orijinalinin yanında <code>shrinkified/</code> klasörüne kaydedilir.",
    compat_label: "Uyumluluk",
    compat_h3: "Dönüştürülen dosyalar cihazlarımda açılır mı?",
    compat_p:
      "H.265 ve HEIF, <strong>yaklaşık 2018</strong> sonrası tüm cihazlarda desteklenen modern standartlardır. Tüm kütüphanenizi dönüştürmeden önce hızlı bir başvuru kaynağı olarak kullanın.",
    compat_p_strong: "yaklaşık 2018",
    compat_good_h4: "✅ İyi destekleniyor",
    compat_good_1:
      'Windows 10 / 11 <span style="color: var(--muted)">(Microsoft Store\'dan ücretsiz HEVC uzantısı)</span>',
    compat_good_2: "macOS High Sierra (10.13) ve üzeri",
    compat_good_3: "iPhone / iPad — iOS 11 ve üzeri",
    compat_good_4: "Android 9 ve üzeri",
    compat_good_5: "2018 ve sonrası akıllı TV'ler",
    compat_good_6: "Her platformda VLC",
    compat_bad_h4: "⚠️ Sorun yaşanabilir",
    compat_bad_1: "Windows 7 / 8 — H.265 veya HEIF için yerli destek yok",
    compat_bad_2: "Android 8 ve öncesi — tutarsız donanım desteği",
    compat_bad_3: "2018 öncesi akıllı TV'ler",
    compat_bad_4: "Eski dijital fotoğraf çerçeveleri",
    compat_footer:
      "Eski cihaz kullanan kişilerle dosya paylaşıyorsanız orijinallerinizi saklayın. Shrinkify <strong>hiçbir zaman silmez</strong>.",
    footer_desc:
      "Medya dosyalarını analiz edin, codec dönüşümleri önerin, kopyaları tespit edin ve ayrıntılı HTML raporu oluşturun. Sonsuza kadar ücretsiz ve açık kaynak.",
    footer_github: "GitHub",
    footer_releases: "Sürümler",
    footer_bug: "Hata bildir",
    footer_made_by:
      '<a href="https://github.com/nazimcanislam" target="_blank">Nazımcan İslam</a> tarafından yapıldı',
    footer_collab:
      '🤝 <a href="https://claude.ai" target="_blank">Claude</a> (Anthropic) ile iş birliği içinde geliştirildi',
  },
};

let currentLang = "en";

function applyLang(lang) {
  const t = translations[lang];
  if (!t) return;
  currentLang = lang;

  // <html lang="">
  document.getElementById("html-root").lang = lang;

  // <title>
  const titleEl = document.querySelector("[data-i18n-title]");
  if (titleEl) titleEl.textContent = t["page_title"];

  // all data-i18n elements
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (t[key] !== undefined) el.innerHTML = t[key];
  });

  // lang button shows the opposite language
  const btn = document.getElementById("lang-btn");
  if (btn) btn.textContent = lang === "tr" ? "🇬🇧 EN" : "🇹🇷 TR";

  localStorage.setItem("shrinkify-lang", lang);
}

function toggleLang() {
  applyLang(currentLang === "tr" ? "en" : "tr");
}

// Detect language on load
(function () {
  const saved = localStorage.getItem("shrinkify-lang");
  if (saved && translations[saved]) {
    applyLang(saved);
  } else {
    const browser = navigator.language || "";
    applyLang(browser.startsWith("tr") ? "tr" : "en");
  }
})();

// ── OS detection ──────────────────────────────────────────────────────
function getOS() {
  // Prefer the modern userAgentData API (Chrome 90+, Edge 90+).
  // navigator.userAgent can be frozen/reduced in newer browsers, making
  // regex matching unreliable — userAgentData.platform is the canonical source.
  if (navigator.userAgentData && navigator.userAgentData.platform) {
    const p = navigator.userAgentData.platform;
    if (p === "Windows") return "Windows";
    if (p === "macOS")   return "macOS";
    if (p === "Linux")   return "Linux";
    if (p === "Android") return "Android";
    // iOS not exposed via userAgentData; fall through to legacy check
  }

  // Legacy fallback for Safari, Firefox, and older browsers
  const ua       = navigator.userAgent || navigator.vendor || window.opera || "";
  const platform = navigator.platform  || "";

  if (
    /iPad|iPhone|iPod/.test(ua) ||
    (platform === "MacIntel" && navigator.maxTouchPoints > 1)
  ) return "iOS";
  if (/Macintosh|MacIntel|MacPPC|Mac68K/.test(ua)) return "macOS";
  if (/android/i.test(ua))                         return "Android";
  if (/Win32|Win64|Windows|WinCE/.test(ua))        return "Windows";
  if (/Linux|X11/.test(ua))                        return "Linux";
  return "unknown";
}

const os = getOS();
const detectedOsClassName = "detected-os";
if (os === "Windows")              document.getElementById("dl-card-windows").classList.add(detectedOsClassName);
else if (os === "macOS")           document.getElementById("dl-card-macos").classList.add(detectedOsClassName);
else if (os === "Linux")           document.getElementById("dl-card-linux").classList.add(detectedOsClassName);
else if (os === "Android" || os === "iOS") document.getElementById("dl-card-mobile").classList.add(detectedOsClassName);

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
