import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from typing import List, Dict, Any
from SPARQLWrapper import SPARQLWrapper, JSON

# --- CONFIGURACIÓN Y CARGA DE ONTOLOGÍAS ---

g = Graph()

# Lista de ontologías a unir
ONTOLOGY_FILES = [
    "ontologia.rdf",              # tu ontología original
    "MobileClassesComplete.owl"   # tu nueva ontología
]

for filename in ONTOLOGY_FILES:
    try:
        g.parse(filename)
        print(f"Ontología '{filename}' cargada. Tripletas acumuladas: {len(g)}")
    except Exception as e:
        print(f"Error al cargar '{filename}': {e}")

# Namespaces de tus ontologías
URI_BASE = "http://www.semanticweb.org/usuario/ontologies/2025/9/untitled-ontology-26#"
URI_BASE2 = "https://www.gsmarena.com/ontologies/mobile.owl#"

ONTO = Namespace(URI_BASE)
ONTO2 = Namespace(URI_BASE2)

# Endpoint externo
DBPEDIA_SPARQL_ENDPOINT = "http://dbpedia.org/sparql"

# FASTAPI configuración
app = FastAPI(
    title="API Ontología Procesadores",
    version="4.1",
    description="Búsqueda local OWL + DBpedia + combinada."
)

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
        if texto.startswith(base):
            return texto.replace(base, "")

    return texto.split("#")[-1]


def origen_ontologia(uri: str) -> str:
    if uri.startswith(URI_BASE):
        return "Ontología Principal (ontologia.rdf)"
    if uri.startswith(URI_BASE2):
        return "Ontología de Móviles (MobileClassesComplete.owl)"
    return "Ontología Desconocida"


def obtener_detalles_contexto(nombre_entidad: str) -> Dict[str, Any]:
    uri_sujeto = URIRef(URI_BASE + nombre_entidad)

    if (uri_sujeto, None, None) not in g:
        return {"id": nombre_entidad, "datos": {}, "relaciones": []}

    datos = {}
    relaciones = []

    for predicado, objeto in g.predicate_objects(uri_sujeto):
        propiedad = limpiar_valor(predicado)

        if propiedad in ["type", "NamedIndividual"]:
            continue

        if isinstance(objeto, URIRef) and (str(objeto).startswith(URI_BASE) or str(objeto).startswith(URI_BASE2)):
            relaciones.append({
                "tipo": propiedad,
                "nombre": limpiar_valor(objeto).replace("_", " ")
            })
        else:
            valor = limpiar_valor(objeto)
            if propiedad in datos:
                if not isinstance(datos[propiedad], list):
                    datos[propiedad] = [datos[propiedad]]
                datos[propiedad].append(valor)
            else:
                datos[propiedad] = valor

    return {
        "id": nombre_entidad,
        "datos": datos,
        "relaciones": relaciones
    }


def consultar_dbpedia(query: str) -> List[Dict[str, Any]]:
    try:
        sparql = SPARQLWrapper(DBPEDIA_SPARQL_ENDPOINT)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        return results.get("results", {}).get("bindings", [])
    except Exception as e:
        print("Error consultando DBpedia:", e)
        return []

# --- 🔥 BÚSQUEDA LOCAL EN OWL (Local 1 + Local 2, soporta "todos") ---

def buscar_local_owl(termino: str) -> List[Dict[str, Any]]:
    # Si el término es "todos", no aplicamos filtro de texto
    if termino == "todos":
        filtro = ""
    else:
        filtro = f"""
        FILTER (
            regex(?modelo, "{termino}", "i") ||
            regex(str(?id), "{termino}", "i")
        )
        """

    consulta_local = f"""
    PREFIX onto: <{URI_BASE}>
    PREFIX mobile: <{URI_BASE2}>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT ?id ?modelo ?fabricante WHERE {{

        ### ---------------- LOCAL 1 (ontologia.rdf) ----------------
        {{
            ?id rdf:type onto:Procesador .
            OPTIONAL {{ ?id onto:modelo ?modelo . }}
            OPTIONAL {{ ?id onto:esFabricadoPor ?fab .
                       ?fab onto:nombre ?fabricante }}
        }}

        UNION

        ### ---------------- LOCAL 2 (MobileClassesComplete.owl, genérico) ----------------
        {{
            ?id ?p ?o .
            FILTER(STRSTARTS(STR(?id), "{URI_BASE2}"))

            # Nombre del modelo si existe
            OPTIONAL {{ ?id rdfs:label ?modelo . }}

            # De momento no tenemos data properties claras para fabricante,
            # aquí podrías añadirlas cuando existan:
            # OPTIONAL {{ ?id mobile:manufacturer ?fabricante . }}
        }}

        {filtro}
    }}
    LIMIT 70
    """

    resultados = g.query(consulta_local)

    datos = []
    for row in resultados:
        uri_str = str(row.id)
        nombre_limpio = limpiar_valor(row.id)

        # ---------- MODELO ----------
        if hasattr(row, "modelo") and row.modelo:
            modelo = str(row.modelo)
        else:
            modelo = nombre_limpio.replace("_", " ")

        # ---------- FABRICANTE ----------
        if hasattr(row, "fabricante") and row.fabricante:
            fabricante = str(row.fabricante)
        else:
            fabricante = "N/A"

        # ---------- DETALLES ----------
        origen = origen_ontologia(uri_str)
        detalles_datos: Dict[str, Any] = {}
        detalles_relaciones: List[Dict[str, Any]] = []

        # Solo para la ontología principal tenemos mapeo detallado
        if "Principal" in origen:
            detalles = obtener_detalles_contexto(nombre_limpio)
            detalles_datos = detalles.get("datos", {})
            detalles_relaciones = detalles.get("relaciones", [])

            # Si sigue sin haber fabricante, intenta sacarlo de las relaciones
            if fabricante == "N/A":
                fab_rel = next(
                    (rel for rel in detalles_relaciones if rel["tipo"] == "esFabricadoPor"),
                    None
                )
                if fab_rel:
                    fabricante = fab_rel["nombre"]

        datos.append({
            "origen": origen,
            "modelo": modelo,
            "fabricante": fabricante,
            "clase": "Procesador",
            "uri": uri_str,
            "detalles_completos": detalles_datos,
            "relaciones_completas": detalles_relaciones
        })

    return datos

# --- BÚSQUEDA ONLINE EN DBPEDIA ---

def buscar_online_dbpedia(termino: str) -> List[Dict[str, Any]]:
    consulta = f"""
    SELECT DISTINCT ?resource ?label WHERE {{
        ?resource rdfs:label ?label .
        FILTER (lang(?label)='en' || lang(?label)='es')
        FILTER (regex(?label, "{termino}", "i"))
        FILTER (STRSTARTS(STR(?resource), "http://dbpedia.org/resource/"))
    }}
    LIMIT 10
    """

    resultados = consultar_dbpedia(consulta)

    datos = []
    for r in resultados:
        datos.append({
            "origen": "DBpedia Online",
            "modelo": r["label"]["value"],
            "fabricante": "Base de Conocimiento General",
            "clase": "Entidad DBpedia",
            "uri": r["resource"]["value"],
            "detalles_completos": {},
            "relaciones_completas": []
        })

    return datos

# --- ENDPOINTS ---

@app.get("/")
def inicio():
    return {
        "estado": "online",
        "tripletas": len(g),
        "namespaces": [URI_BASE, URI_BASE2]
    }

@app.get("/clases")
def listar_clases():
    clases = set()
    query = """
    SELECT DISTINCT ?c WHERE {
        { ?c a rdfs:Class }
        UNION
        { ?c a owl:Class }
    }
    """
    for row in g.query(query, initNs={"rdfs": RDFS, "owl": Namespace("http://www.w3.org/2002/07/owl#")}):
        clases.add(limpiar_valor(row.c))

    excluir = ["Class", "Thing", "NamedIndividual", "AnnotationProperty",
               "ObjectProperty", "DatatypeProperty", "Ontology"]

    return {
        "clases_encontradas": [c for c in clases if c not in excluir]
    }

@app.get("/busqueda-local/{termino}")
def busqueda_local(termino: str):
    resultados = buscar_local_owl(termino)
    return {
        "cantidad_total": len(resultados),
        "resultados": resultados
    }

@app.get("/busqueda-dbpedia/{termino}")
def busqueda_dbpedia(termino: str):
    resultados = buscar_online_dbpedia(termino)
    return {
        "cantidad_total": len(resultados),
        "resultados": resultados
    }

@app.get("/busqueda-global/{termino}")
def busqueda_global(termino: str):
    local = buscar_local_owl(termino)
    dbpedia = buscar_online_dbpedia(termino)

    fusion = local + dbpedia

    return {
        "cantidad_local": len(local),
        "cantidad_dbpedia": len(dbpedia),
        "cantidad_total": len(fusion),
        "resultados": fusion
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
