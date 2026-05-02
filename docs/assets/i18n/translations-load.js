// currentLang is pre-detected by the inline script in <head> to avoid flash.
let currentLang = window.__SHRINKIFY_LANG || "en";

// In-memory cache: both languages stay resident after first load.
// Switching TR→EN→TR never triggers a second network request.
const translationsCache = {};

async function loadLanguage(lang) {
  // Already on this language — nothing to do
  if (lang === currentLang && translationsCache[lang]) return;
  // English with no cache entry means the HTML is the source of truth; just reveal
  if (lang === "en" && !translationsCache[lang] && currentLang === "en") {
    document.documentElement.style.visibility = "";
    return;
  }

  try {
    // Serve from cache if available (e.g. switching back after first load)
    if (!translationsCache[lang]) {
      const response = await fetch(
        `assets/i18n/locales/translation.${lang}.json`,
        {
          // credentials: "omit" so this matches the <link rel="preload" crossorigin="anonymous">
          // preload hint injected by the inline script in <head>.
          credentials: "omit",
          cache: "force-cache",
          mode: "same-origin",
        },
      );
      if (!response.ok) throw new Error(`Lang file could not be loaded: ${lang}`);
      translationsCache[lang] = await response.json();
    }

    currentLang = lang;
    applyTranslations(lang, translationsCache[lang]);
  } catch (error) {
    document.documentElement.style.visibility = "";
    if (lang !== "en") loadLanguage("en");
  }
}

// Init: script is deferred, so DOM is ready here.
(function init() {
  if (currentLang !== "en") {
    loadLanguage(currentLang);
  }
  // English: HTML is already in English; content is already visible.
})();
