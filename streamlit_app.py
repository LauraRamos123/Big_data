import streamlit as st
from pymongo import MongoClient
from neo4j import GraphDatabase
from pyvis.network import Network
import streamlit.components.v1 as components

# =============================================
# 1. CONEXIÓN A MONGODB (TAL CUAL COMO PEDISTE)
# =============================================
MONGO_URI = "mongodb+srv://superuser:ynmkEGkQ4JPPs9sI@cluster0.qfgghrp.mongodb.net/?appName=Cluster0"
DB_NAME = "Proyecto_Final"
COLLECTION_NAME = "Audios_Sentencias"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# =============================================
# 2. CONEXIÓN A NEO4J
# =============================================
URI = "neo4j+s://b29b29cb.databases.neo4j.io"
AUTH = ("neo4j", "D7MvqURA0Ov-q71KDA9ZqkvU2FeEjn2DsIK5RlodsSg")

driver = GraphDatabase.driver(URI, auth=AUTH)

with driver.session(database="neo4j") as session:
    session.run("RETURN 1")

# =============================================
# FUNCIÓN PARA CONSULTAR SIMILITUDES EN NEO4J
# =============================================
def obtener_similitudes(nombre_prov):
    query = """
    MATCH (p:Providencia {nombre: $nombre_prov})-[r:SIMILAR]-(o:Providencia)
    RETURN p.nombre AS origen, o.nombre AS destino, r.score AS similitud
    ORDER BY similitud DESC
    """
    with driver.session(database="neo4j") as session:
        result = session.run(query, nombre_prov=nombre_prov)
        return list(result)

# =============================================
# FUNCIÓN PARA UMBRAL
# =============================================
def obtener_similitudes_filtradas(nombre_prov, umbral):
    query = """
    MATCH (n:Providencia {nombre: $nombre_prov})-[r:SIMILAR]-(m:Providencia)
    WHERE r.score >= $umbral
    RETURN n.nombre AS origen, m.nombre AS destino, r.score AS similitud
    ORDER BY similitud DESC
    """
    with driver.session(database="neo4j") as session:
        result = session.run(query, nombre_prov=nombre_prov, umbral=umbral)
        return list(result)

# ==========================================================
# 🔥 NUEVO: CONSULTAR GRAFO DESDE LISTA DE NOMBRES (Mongo→Neo4j)
# ==========================================================
def obtener_grafo_desde_lista(resultados_mongo):
    lista = [n["providencia"] for n in resultados_mongo if "providencia" in n]

    if len(lista) == 0:
        return []

    query = """
    MATCH (p:Providencia)-[r:SIMILAR]-(o:Providencia)
    WHERE p.nombre IN $lista AND o.nombre IN $lista
    RETURN p.nombre AS origen, o.nombre AS destino, r.score AS similitud
    ORDER BY similitud DESC
    """

    with driver.session(database="neo4j") as session:
        result = session.run(query, lista=lista)
        return list(result)

# =============================================
# FUNCIÓN PARA CREAR GRAFO
# =============================================
def crear_grafo(similitudes, nodo_central=None):
    net = Network(height="500px", width="100%", bgcolor="#FFFFFF", font_color="black")

    if nodo_central:
        net.add_node(nodo_central, label=nodo_central, color="red", size=25)

    for registro in similitudes:
        origen = registro["origen"]
        destino = registro["destino"]
        score = registro["similitud"]

        net.add_node(origen, label=origen, color="blue")
        net.add_node(destino, label=destino, color="blue")
        net.add_edge(origen, destino, title=f"Similitud: {score}", value=score)

    net.repulsion(node_distance=200, spring_length=200)
    return net

# =============================================
# TRUNCAR TEXTO
# =============================================
def truncar_texto(texto, n_palabras=300):
    if not texto:
        return ""
    palabras = texto.split()
    return " ".join(palabras[:n_palabras]) + ("..." if len(palabras) > n_palabras else "")

# =============================================
# TÍTULO
# =============================================
st.title("Buscador de Providencias en MongoDB + Grafo Neo4j")

# =============================================
# SIDEBAR
# =============================================
st.sidebar.header("Filtros de búsqueda")

input_providencia = st.sidebar.text_input("Número de providencia")
input_tipo = st.sidebar.text_input("Tipo de providencia")
input_keywords = st.sidebar.text_input("Palabras clave (separadas por coma)")

buscar = st.sidebar.button("Buscar")

# ---------------------------------------------
# GRAFO MANUAL
# ---------------------------------------------
st.sidebar.header("Grafo por similitud")
grafo_nombre = st.sidebar.text_input("Providencia para grafo")
grafo_umbral = st.sidebar.slider("Similitud mínima", 0.0, 1.0, 0.5, 0.01)
boton_grafo = st.sidebar.button("Generar Grafo")

if boton_grafo and grafo_nombre:
    sims = obtener_similitudes_filtradas(grafo_nombre, grafo_umbral)
    st.subheader(f"Grafo desde `{grafo_nombre}` con similitud ≥ {grafo_umbral}")

    if len(sims) == 0:
        st.info("No hay relaciones.")
    else:
        net = crear_grafo(sims, grafo_nombre)
        net.save_graph("grafo.html")
        HtmlFile = open("grafo.html", "r", encoding="utf-8")
        components.html(HtmlFile.read(), height=550)

# =============================================
# QUERIES BASE
# =============================================
def consulta_por_providencia(nombre):
    return {"providencia": nombre} if nombre else {}

def consulta_por_tipo(tipo):
    return {"tipo": tipo} if tipo else {}

def consulta_por_palabras(keywords):
    if not keywords:
        return {}
    palabras = [p.strip() for p in keywords.split(",") if p.strip()]
    return {"Texto": {"$regex": "|".join(palabras), "$options": "i"}}

def armar_query(providencia, tipo, keywords):
    query = {}
    query.update(consulta_por_providencia(providencia))
    query.update(consulta_por_tipo(tipo))
    query.update(consulta_por_palabras(keywords))
    return query

# =============================================
# EJECUTAR CONSULTA MONGO + INTEGRAR GRAFO
# =============================================
if buscar:
    query = armar_query(input_providencia, input_tipo, input_keywords)
    st.write("### Query generada:")
    st.code(str(query))

    resultados = list(collection.find(query))
    st.write(f"### Resultados ({len(resultados)})")

    if len(resultados) == 0:
        st.info("No se encontraron documentos.")

    if input_tipo or input_keywords:
        st.subheader("Grafo de las providencias filtradas (Neo4j)")
        sims = obtener_grafo_desde_lista(resultados)

        if len(sims) == 0:
            st.info("No hay relaciones de similitud entre los resultados.")
        else:
            net = crear_grafo(sims)
            net.save_graph("grafo.html")
            HtmlFile = open("grafo.html", "r", encoding="utf-8")
            components.html(HtmlFile.read(), height=550)

    # ==========================================
    # MOSTRAR LOS DOCUMENTOS
    # ==========================================
    for doc in resultados:
        prov = doc.get("providencia")

        with st.expander(f"Providencia: {prov} | Tipo: {doc.get('tipo', 'N/A')}"):

            doc_mostrar = doc.copy()
            doc_mostrar["Texto"] = truncar_texto(doc.get("Texto", ""), 300)
            st.write(doc_mostrar)

            # Grafo individual por providencia
            if prov:
                st.subheader("Grafo de similitudes (Neo4j)")

                sims = obtener_similitudes(prov)

                if len(sims) == 0:
                    st.info("Esta providencia no tiene relaciones.")
                else:
                    net = crear_grafo(sims, prov)
                    net.save_graph("grafo.html")
                    HtmlFile = open("grafo.html", "r", encoding="utf-8")
                    components.html(HtmlFile.read(), height=550)

                    # ============================
                    # 🔥 LISTA DE SIMILITUDES (NUEVO)
                    # ============================
                    st.subheader("Listado de similitudes")

                    for r in sims:
                        origen = r["origen"]
                        destino = r["destino"]
                        score = r["similitud"]
                        st.write(f"- **{destino}** → similitud: **{score}**")
