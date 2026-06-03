/**
 * i18n bootstrap. Loads translations from the JSON files in this folder,
 * detects browser language on first visit, then persists the user's choice
 * to localStorage so it sticks across sessions.
 *
 * Adding a new language:
 *   1. Drop `<code>.json` in this folder mirroring en.json's key tree.
 *   2. Import + register it below.
 *   3. Add the language to LANGUAGES so it appears in the picker.
 *
 * Adding a new translatable string:
 *   1. Add the English source to en.json.
 *   2. Use `useTranslation` in the component: `const { t } = useTranslation()`;
 *      then `t("namespace.key")`.
 *   3. Translate the new key in every other language file. Missing keys fall
 *      back to English at runtime so the UI never shows the raw key.
 */
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import en from "./en.json";
import hi from "./hi.json";
import ta from "./ta.json";

export const LANGUAGES = [
  { code: "en", name: "English", nativeName: "English" },
  { code: "hi", name: "Hindi", nativeName: "हिन्दी" },
  { code: "ta", name: "Tamil", nativeName: "தமிழ்" },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]["code"];

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      hi: { translation: hi },
      ta: { translation: ta },
    },
    fallbackLng: "en",
    supportedLngs: LANGUAGES.map((l) => l.code),
    interpolation: { escapeValue: false }, // React already escapes
    detection: {
      // Priority order — we check localStorage first (user's saved choice),
      // then fall back to browser settings on a fresh device.
      order: ["localStorage", "navigator"],
      lookupLocalStorage: "anjaneya-lang",
      caches: ["localStorage"],
    },
  });

export default i18n;
