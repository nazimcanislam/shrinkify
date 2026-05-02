function applyTranslations(lang, translations) {
  const t = translations;

  document.getElementById("html-root").lang = lang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (t[key] !== undefined) el.innerHTML = t[key];
  });

  document.querySelectorAll("[data-i18n-title]").forEach((el) => {
    const key = el.dataset.i18nTitle;
    if (t[key] !== undefined) el.textContent = t[key];
  });

  const btn = document.getElementById("lang-btn");
  if (btn) btn.textContent = lang === "tr" ? "🇬🇧 EN" : "🇹🇷 TR";

  // Reveal page (was hidden by inline script to prevent language flash)
  document.documentElement.style.visibility = "";
}

function toggleLang() {
  const lang = currentLang === "tr" ? "en" : "tr";
  loadLanguage(lang);
  localStorage.setItem("shrinkify-lang", lang);
}

const langBtn = document.getElementById("lang-btn");
if (langBtn) {
  langBtn.addEventListener("click", toggleLang);
}
