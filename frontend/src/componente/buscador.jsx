// src/buscador.jsx
import React, { useState, useEffect, useCallback } from "react";
import "../styles/buscador.css";
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
    faSearch,
    faGlobe,
    faMicrochip,
    faDatabase,
    faSpinner,
    faCircleExclamation
} from '@fortawesome/free-solid-svg-icons';
import fondo from '../assets/fondo.png';
import { useTranslation } from 'react-i18next';
import i18n from '../i18n';

const API_BASE_URL = "http://127.0.0.1:8000";

const Buscador = () => {
    const { t } = useTranslation();

    const [searchTerm, setSearchTerm] = useState('');
    const [endpoint, setEndpoint] = useState('global');
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expandedCards, setExpandedCards] = useState({});
    const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

    const toggleCard = (key) => {
        setExpandedCards(prev => ({ ...prev, [key]: !prev[key] }));
    };

    // ============================================================
    // FUNCIÓN PRINCIPAL DE BUSQUEDA (ARREGLADA)
    // ============================================================
    const performSearch = useCallback(async (term, currentEndpoint) => {
        setLoading(true);
        setError(null);

        try {
            const cleanTerm = term.trim() === "" ? "todos" : term.trim();
            const url = `${API_BASE_URL}/busqueda-${currentEndpoint}/${cleanTerm}`;

            const response = await fetch(url);
            if (!response.ok)
                throw new Error(`Error ${response.status}: La API no respondió correctamente.`);

            const data = await response.json();
            setResults(data.resultados ?? []);
        } catch (err) {
            console.error("Error en la búsqueda:", err);
            setError(err.message);
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, []);

    // ============================================================
    // CONTROL DE RECOMENDADOS SEGÚN APARTADO
    // ============================================================
    useEffect(() => {
        // si no hay texto -> mostrar recomendados siempre
        if (searchTerm.trim() === "") {
            performSearch("", endpoint);
        }
    }, [endpoint, searchTerm, performSearch]);

    // ============================================================
    // RENDER TARJETAS
    // ============================================================
    const renderCard = (item, index) => {
        const key = item.uri ? `${item.uri}-${index}` : `local-item-${index}`;
        const origen = item.origen || "";

        const isDbpedia = origen.includes("DBpedia");
        const isLocal1 = origen.includes("Principal");
        const isLocal2 = origen.includes("Móviles");
        const isLocal = isLocal1 || isLocal2;

        const expanded = expandedCards[key];

        let contenido;

        if (isLocal) {
            const datos = item.detalles_completos || {};
            const cores = datos.numeroDeNucleos || "N/A";
            const freq = datos.frecuenciaMaxGHz ? `${datos.frecuenciaMaxGHz} GHz` : "N/A";
            const gpu = item.relaciones_completas?.find(r => r.tipo === 'tieneGPU')?.nombre || "N/A";

            contenido = (
                <>
                    <p className="card-spec"><strong>{t('manufacturer')}:</strong> {item.fabricante}</p>

                    {expanded && (
                        <>
                            <p className="card-spec"><strong>{t('cores')}:</strong> {cores}</p>
                            <p className="card-spec"><strong>{t('frequency')}:</strong> {freq}</p>
                            <p className="card-spec"><strong>{t('gpu')}:</strong> {gpu}</p>
                        </>
                    )}

                    <button className="detail-btn" onClick={() => toggleCard(key)}>
                        {expanded ? t('hideDetails') : t('viewDetails')}
                    </button>
                </>
            );
        } else {
            contenido = (
                <>
                    <p className="card-spec">
                        <strong>URI:</strong>{" "}
                        <a href={item.uri} target="_blank" rel="noopener noreferrer">
                            {item.uri.split("/").pop()}
                        </a>
                    </p>

                    <p className="card-spec">{t('dbpediaEntity')}</p>
                </>
            );
        }

        let tagText = "";
        let tagBg = "";
        let tagEmoji = "";

        if (isLocal1) {
            tagText = "LOCAL 1"; tagBg = "#22c55e"; tagEmoji = "📗";
        } else if (isLocal2) {
            tagText = "LOCAL 2"; tagBg = "#3b82f6"; tagEmoji = "📘";
        } else if (isDbpedia) {
            tagText = t('dbpediaLabel'); tagBg = "#0ea5e9"; tagEmoji = "🌐";
        } else {
            tagText = origen || "Unknown"; tagBg = "#6b7280"; tagEmoji = "❓";
        }

        return (
            <div key={key} className={`result-card full-detail ${isDbpedia ? "card-dbpedia" : "card-local"}`}>
                <span className="card-source-tag"
                    style={{
                        backgroundColor: tagBg,
                        color: "white",
                        padding: "4px 10px",
                        borderRadius: "999px",
                        fontSize: "0.8rem",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "6px"
                    }}>
                    <span>{tagEmoji}</span> <span>{tagText}</span>
                </span>

                <h3 className="card-title">
                    <FontAwesomeIcon icon={isDbpedia ? faGlobe : faMicrochip} />
                    {" "}{item.modelo}
                </h3>

                {contenido}
            </div>
        );
    };

    // ============================================================
    // UI
    // ============================================================
    return (
        <div className="buscador-container" style={{
            backgroundImage: `url(${fondo})`,
            backgroundSize: 'cover',
            minHeight: '100vh'
        }}>
            <div className="overlay"></div>

            {/* HEADER */}
            <div className="header-banner">
                <h1 className="main-title">{t('PROCESADORES DE CELULARES')}</h1>

                <div className="search-box">
                    <FontAwesomeIcon icon={faSearch} className="search-icon" />

                    <input
                        type="text"
                        className="search-input"
                        placeholder={t('searchPlaceholder')}
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                    />

                    <button className="search-btn" onClick={() => performSearch(searchTerm, endpoint)}>
                        {t('searchButton')}
                    </button>
                </div>

                {/* FILTROS */}
                <div className="filter-buttons">
                    {[
                        { ep: "global", label: t('combined'), icon: faGlobe },
                        { ep: "local", label: t('local'), icon: faMicrochip },
                        { ep: "dbpedia", label: t('dbpedia'), icon: faDatabase }
                    ].map(({ ep, label, icon }) => (
                        <button
                            key={ep}
                            className={`filter-btn ${endpoint === ep ? "active" : ""}`}
                            onClick={() => setEndpoint(ep)}
                        >
                            <FontAwesomeIcon icon={icon} /> {label}
                        </button>
                    ))}

                    <select
                        className="language-select"
                        onChange={(e) => {
                            i18n.changeLanguage(e.target.value);
                            setCurrentLanguage(e.target.value);
                        }}
                        value={currentLanguage}
                    >
                        <option value="es">🇪🇸 ES</option>
                        <option value="en">🇬🇧 EN</option>
                        <option value="fr">🇫🇷 FR</option>
                    </select>
                </div>
            </div>

            {/* RESULTADOS */}
            <div className="main-content">
                {loading && (
                    <div className="status-message">
                        <FontAwesomeIcon icon={faSpinner} spin /> {t('loading')}
                    </div>
                )}

                {!loading && error && (
                    <div className="status-message error-message">
                        <FontAwesomeIcon icon={faCircleExclamation} /> {error}
                    </div>
                )}

                {!loading && !error && (
                    <>
                        <div className="results-summary">
                            {t('resultsFrom', { count: results.length, endpoint: endpoint.toUpperCase() })}
                        </div>

                        <div className="results-grid">
                            {results.length > 0
                                ? results.map(renderCard)
                                : <p className="no-results">{t('noResults')}</p>
                            }
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default Buscador;
