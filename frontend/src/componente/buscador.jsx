
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
const BACKEND_PING_TIMEOUT = 1500; // ms

const Buscador = () => {
    const { t } = useTranslation();

    const [searchTerm, setSearchTerm] = useState('');
    const [endpoint, setEndpoint] = useState('global'); // "global" | "local" | "dbpedia"
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [expandedCards, setExpandedCards] = useState({});
    const [currentLanguage, setCurrentLanguage] = useState(i18n.language);

    // Conexión de red y disponibilidad del backend
    const [online, setOnline] = useState(navigator.onLine);
    const [backendReachable, setBackendReachable] = useState(false);

    // Toggle tarjeta
    const toggleCard = (key) => {
        setExpandedCards(prev => ({ ...prev, [key]: !prev[key] }));
    };

    // -------------------------------------------------------
    // Helper: ping al backend con timeout
    // -------------------------------------------------------
    const checkBackendReachable = useCallback(async () => {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), BACKEND_PING_TIMEOUT);

        try {
            const resp = await fetch(`${API_BASE_URL}/`, { method: "GET", signal: controller.signal });
            clearTimeout(id);
            return resp.ok;
        } catch (e) {
            clearTimeout(id);
            return false;
        }
    }, []);

    // Escuchar cambios de conexión y comprobar backend
    useEffect(() => {
        const handleOnline = () => setOnline(true);
        const handleOffline = () => setOnline(false);

        window.addEventListener("online", handleOnline);
        window.addEventListener("offline", handleOffline);

        // Comprobación inicial del backend
        let mounted = true;
        (async () => {
            const reachable = await checkBackendReachable();
            if (mounted) setBackendReachable(reachable);
        })();

        return () => {
            mounted = false;
            window.removeEventListener("online", handleOnline);
            window.removeEventListener("offline", handleOffline);
        };
    }, [checkBackendReachable]);

    // También vuelve a comprobar backend cuando cambie el estado online
    useEffect(() => {
        let mounted = true;
        (async () => {
            const reachable = await checkBackendReachable();
            if (mounted) setBackendReachable(reachable);
        })();
        return () => { mounted = false; };
    }, [online, checkBackendReachable]);

    // -------------------------------------------------------
    // FUNCIÓN PRINCIPAL DE BÚSQUEDA
    // -------------------------------------------------------
    const performSearch = useCallback(async (term, currentEndpoint) => {
        setLoading(true);
        setError(null);

        try {
            const cleanTerm = term.trim() === "" ? "todos" : term.trim();

            // 1) Petición a /busqueda-local
            const localUrl = `${API_BASE_URL}/busqueda-local/${encodeURIComponent(cleanTerm)}`;
            const localResp = await fetch(localUrl);
            if (!localResp.ok) throw new Error(`Error ${localResp.status} al obtener datos locales.`);

            const localJson = await localResp.json();
            const localAll = localJson.resultados ?? [];

            // Separar Local1 / Local2 según 'origen'
            const isLocal1Origin = (o) =>
                String(o || "").toLowerCase().includes("principal") ||
                String(o || "").toLowerCase().includes("local 1") ||
                String(o || "").toLowerCase().includes("ontología principal");

            const isLocal2Origin = (o) =>
                String(o || "").toLowerCase().includes("móviles") ||
                String(o || "").toLowerCase().includes("local 2") ||
                String(o || "").toLowerCase().includes("ontología de móviles");

            const local1Results = localAll.filter(r => isLocal1Origin(r.origen));
            const local2Results = localAll.filter(r => isLocal2Origin(r.origen));

            // Construir array final según estado de red/backend y endpoint
            let final = [];

            if (currentEndpoint === "local") {
                final.push(...local1Results);
                if (!backendReachable || !online) {
                    final.push(...local2Results);
                }
            } else if (currentEndpoint === "dbpedia") {
                // Solo DBpedia si hay backend y conexión
                if (online && backendReachable) {
                    try {
                        const dbUrl = `${API_BASE_URL}/busqueda-dbpedia/${encodeURIComponent(cleanTerm)}`;
                        const dbResp = await fetch(dbUrl);
                        if (dbResp.ok) {
                            const dbJson = await dbResp.json();
                            final.push(...(dbJson.resultados ?? []));
                        } else {
                            throw new Error(`Error ${dbResp.status} al consultar DBpedia.`);
                        }
                    } catch (dbErr) {
                        console.warn("No se pudo obtener DBpedia:", dbErr);
                        setError("No se pudo obtener DBpedia.");
                    }
                }
            } else if (currentEndpoint === "global") {
                // Global: Local1 + DBpedia si posible, Local2 si offline
                final.push(...local1Results);

                if (online && backendReachable) {
                    try {
                        const dbUrl = `${API_BASE_URL}/busqueda-dbpedia/${encodeURIComponent(cleanTerm)}`;
                        const dbResp = await fetch(dbUrl);
                        if (dbResp.ok) {
                            const dbJson = await dbResp.json();
                            final.push(...(dbJson.resultados ?? []));
                        }
                    } catch (dbErr) {
                        console.warn("No se pudo obtener DBpedia:", dbErr);
                    }
                } else {
                    final.push(...local2Results);
                }
            }

            setResults(final);
        } catch (err) {
            console.error("Error en la búsqueda:", err);
            setError(err.message || String(err));
            setResults([]);
        } finally {
            setLoading(false);
        }
    }, [online, backendReachable]);

    // Control: buscar al montar o cuando cambien endpoint/search
    useEffect(() => {
        if (searchTerm.trim() === "") {
            performSearch("", endpoint);
        }
    }, [endpoint, searchTerm, performSearch]);

    // -------------------------------------------------------
    // RENDER TARJETAS
    // -------------------------------------------------------
    const renderCard = (item, index) => {
        const key = item.uri ? `${item.uri}-${index}` : `local-item-${index}`;
        const origen = item.origen || "";

        const isDbpedia = String(origen || "").toLowerCase().includes("dbpedia");
        const isLocal1 = String(origen || "").toLowerCase().includes("principal") ||
                         String(origen || "").toLowerCase().includes("local 1") ||
                         String(origen || "").toLowerCase().includes("ontología principal");
        const isLocal2 = String(origen || "").toLowerCase().includes("móviles") ||
                         String(origen || "").toLowerCase().includes("local 2") ||
                         String(origen || "").toLowerCase().includes("ontología de móviles");
        const isLocal = isLocal1 || isLocal2;

        const expanded = expandedCards[key];

        let contenido;
        if (isLocal) {
            const datos = item.detalles_completos || {};
            const cores = datos.numeroDeNucleos || datos.numero_de_nucleos || "N/A";
            const freq = datos.frecuenciaMaxGHz ? `${datos.frecuenciaMaxGHz} GHz` : (datos.frecuencia_max_g_hz ? `${datos.frecuencia_max_g_hz} GHz` : "N/A");
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
                            {item.uri ? (item.uri.split("/").pop() || item.uri) : "N/A"}
                        </a>
                    </p>
                    <p className="card-spec">{t('dbpediaEntity')}</p>
                </>
            );
        }

        let tagText = "";
        let tagBg = "";
        let tagEmoji = "";

        if (isLocal1) { tagText = "LOCAL 1"; tagBg = "#22c55e"; tagEmoji = "📗"; }
        else if (isLocal2) { tagText = "LOCAL 2"; tagBg = "#3b82f6"; tagEmoji = "📘"; }
        else if (isDbpedia) { tagText = t('dbpediaLabel'); tagBg = "#0ea5e9"; tagEmoji = "🌐"; }
        else { tagText = origen || "Unknown"; tagBg = "#6b7280"; tagEmoji = "❓"; }

        return (
            <div key={key} className={`result-card full-detail ${isDbpedia ? "card-dbpedia" : "card-local"}`}>
                <span className="card-source-tag" style={{
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
                    <FontAwesomeIcon icon={isDbpedia ? faGlobe : faMicrochip} /> {item.modelo}
                </h3>

                {contenido}
            </div>
        );
    };

    // -------------------------------------------------------
    // UI
    // -------------------------------------------------------
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
                    <button
                        className="search-btn"
                        onClick={() => performSearch(searchTerm, endpoint)}
                    >
                        {t('searchButton')}
                    </button>
                </div>

                {/* FILTROS */}
                <div className="filter-buttons">
                    {[{ ep: "global", label: t('combined'), icon: faGlobe },
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
                {/* estado de conexión/backend */}
                <div style={{ marginBottom: 10 }}>
                    <strong style={{ color: online ? "lime" : "orange" }}>
                        {online ? "🟢 Red: conectado" : "🔴 Red: sin conexión"}
                    </strong>{" — "}
                    <span style={{ color: backendReachable ? "lightgreen" : "lightcoral" }}>
                        {backendReachable ? "Backend OK" : `Backend no accesible en ${API_BASE_URL}`}
                    </span>
                    <div style={{ fontSize: 12, color: "#ddd", marginTop: 4 }}>
                        
                    </div>
                </div>

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