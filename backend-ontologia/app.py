import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rdflib import Graph, Literal, URIRef
from typing import List, Dict, Any
from SPARQLWrapper import SPARQLWrapper, JSON

# --- CONFIGURACIÓN ---
g = Graph()
# Asegúrate de que los nombres sean EXACTOS a los de tu carpeta
ONTOLOGY_FILES = ["ontologia.rdf", "MobileClassesComplete.owl"]

print("\n" + "="*60)
print("🚀 SISTEMA SEMÁNTICO V-FINAL: EXTRACCIÓN DETALLADA")
print("="*60)

for filename in ONTOLOGY_FILES:
    try:
        g.parse(filename)
        print(f"✅ Local cargado: '{filename}'")
    except Exception as e:
        print(f"❌ Error cargando '{filename}': {e}")

URI_BASE = "http://www.semanticweb.org/usuario/ontologies/2025/9/untitled-ontology-26#"
URI_BASE2 = "https://www.gsmarena.com/ontologies/mobile.owl#"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- FUNCIONES AUXILIARES ---

def limpiar_valor(uri_o_literal):
    if isinstance(uri_o_literal, Literal):
        return str(uri_o_literal)

    texto = str(uri_o_literal)


    for base in [URI_BASE, URI_BASE2]:
        if s.startswith(base): return s.replace(base, "")
    return s.split("#")[-1]

def origen_ontologia(uri: str) -> str:
    if uri.startswith(URI_BASE): return "Local (Principal)"
    if uri.startswith(URI_BASE2): return "Local (Móviles)"
    return "Local"

# --- 🔍 FUNCIÓN CLAVE: EXTRAER DETALLES PROFUNDOS ---
def obtener_detalles_local(nombre_entidad: str) -> Dict[str, Any]:
    # Reconstruimos la URI completa del recurso
    uri_sujeto = URIRef(URI_BASE + nombre_entidad)
    
    # Si no existe en el grafo, intentamos con la segunda base
    if (uri_sujeto, None, None) not in g:
        uri_sujeto = URIRef(URI_BASE2 + nombre_entidad)
        if (uri_sujeto, None, None) not in g:
            return {}

    detalles = {}
    
    # Recorremos TODAS las propiedades del procesador
    for predicado, objeto in g.predicate_objects(uri_sujeto):
        nombre_propiedad = limpiar_valor(predicado)
        
        # Saltamos propiedades técnicas que no sirven al usuario
        if nombre_propiedad in ["type", "NamedIndividual", "label", "sameAs"]: 
            continue

        valor_final = ""

        # CASO A: El valor es un ENLACE a otra cosa (ej: enlace al individuo 'Qualcomm')
        if isinstance(objeto, URIRef):
            nombre_objeto = limpiar_valor(objeto) # Primero tomamos el ID (ej: Qualcomm)
            
            # Intentamos buscar si ese objeto tiene una etiqueta (label/nombre) más bonita
            labels = []
            for _, label in g.predicate_objects(objeto):
                p_str = limpiar_valor(_).lower()
                if "nombre" in p_str or "label" in p_str or "name" in p_str:
                    labels.append(str(label))
            
            # Si encontramos un nombre bonito, lo usamos; si no, usamos el ID limpio
            valor_final = labels[0] if labels else nombre_objeto.replace("_", " ")

        # CASO B: El valor es TEXTO o NÚMERO (Literal)
        else:
            valor_final = str(objeto).replace("_", " ")

        # Guardamos en el diccionario (agrupando si hay repetidos)
        if nombre_propiedad in detalles:
            if not isinstance(detalles[nombre_propiedad], list):
                detalles[nombre_propiedad] = [detalles[nombre_propiedad]]
            detalles[nombre_propiedad].append(valor_final)
        else:
            detalles[nombre_propiedad] = valor_final

    return detalles

# --- BÚSQUEDA LOCAL ---
def buscar_local_owl(termino: str) -> List[Dict]:
    t = termino.lower().strip()
    es_ranking = False
    etiqueta = ""
    query = ""
    
    # 1. Lógica de preguntas (Mejor, Barato, Nuevo)
    if any(x in t for x in ["mejor", "potente", "rapido", "top"]):
        es_ranking = True; etiqueta = "Puntaje"
        query = f"""
        PREFIX onto: <{URI_BASE}>
        SELECT DISTINCT ?id ?modelo ?fabricante ?valor WHERE {{
            ?id rdf:type onto:Procesador . OPTIONAL {{ ?id onto:modelo ?modelo }}
            OPTIONAL {{ ?id onto:esFabricadoPor ?fab . ?fab onto:nombre_fabricante ?fabricante }}
            OPTIONAL {{ ?id onto:tieneRendimiento ?rend . ?rend onto:benchmark_geekbench_multi ?valor }}
        }} ORDER BY DESC(?valor) LIMIT 20"""
    elif any(x in t for x in ["barato", "economico"]):
        es_ranking = True; etiqueta = "Gama Baja"
        query = f"""
        PREFIX onto: <{URI_BASE}>
        SELECT DISTINCT ?id ?modelo ?fabricante ?valor WHERE {{
            ?id rdf:type onto:Procesador . OPTIONAL {{ ?id onto:modelo ?modelo }}
            OPTIONAL {{ ?id onto:esFabricadoPor ?fab . ?fab onto:nombre_fabricante ?fabricante }}
            OPTIONAL {{ ?id onto:tieneRendimiento ?rend . ?rend onto:benchmark_geekbench_multi ?valor }}
        }} ORDER BY ASC(?valor) LIMIT 20"""
    elif any(x in t for x in ["nuevo", "reciente"]):
        es_ranking = True; etiqueta = "Año"
        query = f"""
        PREFIX onto: <{URI_BASE}>
        SELECT DISTINCT ?id ?modelo ?fabricante ?valor WHERE {{
            ?id rdf:type onto:Procesador . OPTIONAL {{ ?id onto:modelo ?modelo }}
            OPTIONAL {{ ?id onto:esFabricadoPor ?fab . ?fab onto:nombre_fabricante ?fabricante }}
            OPTIONAL {{ ?id onto:anio_lanzamiento ?valor }}
        }} ORDER BY DESC(?valor) LIMIT 20"""
    else:
        # Búsqueda normal
        clean = t.replace("procesador", "").replace("todos", "").strip()
        filtro = "" if not clean else f'FILTER (regex(?modelo, "{clean}", "i") || regex(str(?id), "{clean}", "i"))'
        query = f"""
        PREFIX onto: <{URI_BASE}>
        PREFIX mobile: <{URI_BASE2}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?id ?modelo ?fabricante WHERE {{
            {{ ?id rdf:type onto:Procesador . OPTIONAL {{ ?id onto:modelo ?modelo }} OPTIONAL {{ ?id onto:esFabricadoPor ?fab . ?fab onto:nombre_fabricante ?fabricante }} }}
            UNION
            {{ ?id ?p ?o . FILTER(STRSTARTS(STR(?id), "{URI_BASE2}")) OPTIONAL {{ ?id rdfs:label ?modelo }} }}
            {filtro}
        }} LIMIT 50"""

    try:
        res = g.query(query)
        datos = []
        for r in res:
            uri = str(r.id)
            nom = str(r.modelo) if (hasattr(r, "modelo") and r.modelo) else limpiar_valor(r.id).replace("_", " ")
            
            # Intentamos obtener detalles PROFUNDOS
            detalles = obtener_detalles_local(limpiar_valor(r.id))
            
            # Intentar sacar fabricante del SPARQL o de los detalles
            fab = "N/A"
            if hasattr(r, "fabricante") and r.fabricante:
                fab = str(r.fabricante)
            elif "esFabricadoPor" in detalles:
                fab = detalles["esFabricadoPor"]
            elif "hasManufacturer" in detalles:
                fab = detalles["hasManufacturer"]

            if es_ranking and hasattr(r, "valor") and r.valor: nom = f"{nom} ({etiqueta}: {r.valor})"

            datos.append({
                "origen": origen_ontologia(uri),
                "modelo": nom,
                "fabricante": fab,
                "uri": uri,
                "detalles": detalles # Enviamos TODO lo que encontramos
            })
        return datos
    except Exception as e: 
        print(f"Error Local: {e}")
        return []

# --- BÚSQUEDA DBPEDIA (CON RESPALDO DE SEGURIDAD) ---
def buscar_online_dbpedia(termino: str) -> List[Dict]:
    t = termino.lower().strip()
    
    # Definir palabras clave y modo
    modo = "general"
    if any(x in t for x in ["mejor", "potente", "rapido", "top"]):
        keywords = "'Snapdragon 8' OR 'Apple A17' OR 'Apple M' OR 'Dimensity 9300'"
        modo = "top"
    elif any(x in t for x in ["barato", "economico"]):
        keywords = "'Snapdragon 4' OR 'Helio G' OR 'Unisoc'"
        modo = "low"
    elif any(x in t for x in ["nuevo", "reciente"]):
        keywords = "'Gen 3' OR 'A17' OR 'M3' OR '2400'"
        modo = "new"
    else:
        stopwords = ["cual", "es", "el", "la", "procesador", "cpu", "movil", "celular"]
        words = [w for w in t.split() if w not in stopwords]
        keywords = " OR ".join([f"'{w}'" for w in words])
        if not keywords: keywords = "'System on a chip'"

    # Consulta SPARQL
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    SELECT DISTINCT ?resource ?label ?abstract WHERE {{
        ?resource rdfs:label ?label .
        ?label bif:contains "{keywords}" .
        FILTER (lang(?label) = "en")
        ?resource dbo:abstract ?abstract .
        FILTER (lang(?abstract) = "en")
        FILTER (regex(?abstract, "mobile processor|system on a chip|smartphone|cpu", "i"))
    }} LIMIT 20
    """

    datos = []
    try:
        sparql = SPARQLWrapper("https://dbpedia.org/sparql")
        sparql.setReturnFormat(JSON)
        sparql.setQuery(query)
        sparql.setTimeout(5)
        results = sparql.query().convert()
        
        vistos = set()
        for r in results.get("results", {}).get("bindings", []):
            uri = r["resource"]["value"]
            label = r["label"]["value"]
            if uri in vistos: continue
            if "List of" in label: continue
            vistos.add(uri)
            abstract = r.get("abstract", {}).get("value", "")[:100] + "..."
            datos.append({
                "origen": "DBpedia",
                "modelo": label,
                "fabricante": "Web",
                "uri": uri,
                "detalles": {"Info": abstract}
            })
    except: pass

    # RESPALDO MANUAL SI DBPEDIA FALLA
    if len(datos) == 0:
        lista = []
        if modo == "top": lista = [("Snapdragon 8 Gen 3", "Qualcomm"), ("Apple A17 Pro", "Apple"), ("Dimensity 9300", "MediaTek")]
        elif modo == "low": lista = [("Helio G99", "MediaTek"), ("Snapdragon 695", "Qualcomm"), ("Unisoc T612", "Unisoc")]
        elif modo == "new": lista = [("Apple M3", "Apple"), ("Exynos 2400", "Samsung")]
        else: lista = [("Qualcomm Snapdragon", "Qualcomm"), ("Apple Silicon", "Apple"), ("Samsung Exynos", "Samsung")]

        for m, f in lista:
            datos.append({
                "origen": "DBpedia (Respaldo)",
                "modelo": m,
                "fabricante": f,
                "uri": "http://dbpedia.org",
                "detalles": {"Info": "Datos cargados por respaldo."}
            })

    return datos

# --- ENDPOINTS ---
@app.get("/")
def home(): return {"status": "ok"}

@app.get("/busqueda-local/{termino}")
def local_ep(termino: str):
    res = buscar_local_owl(termino)
    return {"cantidad_total": len(res), "resultados": res}

@app.get("/busqueda-dbpedia/{termino}")
def dbpedia_ep(termino: str):
    res = buscar_online_dbpedia(termino)
    return {"cantidad_total": len(res), "resultados": res}

@app.get("/busqueda-global/{termino}")
def global_ep(termino: str):
    l = buscar_local_owl(termino)
    d = buscar_online_dbpedia(termino)
    return {"cantidad_local": len(l), "cantidad_dbpedia": len(d), "cantidad_total": len(l)+len(d), "resultados": l + d}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
