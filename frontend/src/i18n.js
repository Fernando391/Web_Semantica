// Importaciones necesarias
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

// Importa los archivos JSON con traducciones
import en from "./locales/en.json";
import es from "./locales/es.json";
import fr from "./locales/fr.json";

// Configuración de i18next
i18n
  .use(LanguageDetector) // Detecta idioma automáticamente
  .use(initReactI18next) // Pasa i18n a react-i18next
  .init({
    resources: {
      en: { translation: en },
      es: { translation: es },
      fr: { translation: fr },
    },
    fallbackLng: "es", // Idioma por defecto
    interpolation: { escapeValue: false },
  });

// Exportamos i18n para usarlo en otros componentes
export default i18n;

