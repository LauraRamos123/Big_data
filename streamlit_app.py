import streamlit as st
from pymongo import MongoClient
from neo4j import GraphDatabase
import networkx as nx
import matplotlib.pyplot as plt
import streamlit.components.v1 as components

# ================================
# 🎨 ESTILOS PERSONALIZADOS
# ================================
st.markdown("""
<style>

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Reducir ancho del sidebar */
[data-testid="stSidebar"] {
    width: 260px !important;
}

/* Contenedor para gráficos */
.graph-box {
    background-color: #111827;
    padding: 20px;
    border-radius: 20px;
    margin-top: 20px;
    margin-bottom: 25px;
}

/* Separador */
hr {
    border: 0;
    height: 1px;
    background: #374151;
    margin-top: 20px;
    margin-bottom: 20px;
}

/* Expander estilizado */
details > summary {
    font-size: 18px;
    font-weight: 600;
}

</style>
""", unsafe_allow_html=True)

# =============================================
# 1. CONEXIÓN A MONGODB
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

# =============================================
# GRAFO FILTRADO DESDE LISTA
# =============================================
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
# 🎨 DIBUJAR GRAFO
# =============================================
def crear_grafo(sims, highlight=None):
    
    G = nx.Graph()

    for r in sims:
        origen = r["origen"]
        destino = r["destino"]
        score = r["similitud"]
        G.add_edge(origen, destino, weight=score)

    pos = nx.spring_layout(G, seed=42, k=1.0)

    plt.figure(figsize=(13, 13))

    node_size = 7000    
    font_size = 18

    node_colors = []
    for n in G.nodes():
        if highlight and n == highlight:
            node_colors.append("#FF4040")
        else:
            node_colors.append("#4A90E2")

    edges = G.edges(data=True)
    edge_colors = []
    edge_widths = []

    for u, v, data in edges:
        score = data["weight"]

        if score >= 0.25:
            color = "#1C5D99"; width = 3.5
        elif score >= 0.15:
            color = "#3A7CA5"; width = 2.5
        elif score >= 0.05:
            color = "#95C8D8"; width = 1.8
        else:
            color = "#CCCCCC"; width = 1

        edge_colors.append(color)
        edge_widths.append(width)

    nx.draw_networkx_nodes(G, pos, node_size=node_size, node_color=node_colors, alpha=0.95)
    nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color=edge_colors, alpha=0.8)
    nx.draw_networkx_labels(G, pos, font_size=font_size, font_color="black", font_weight="bold")

    plt.axis("off")
    plt.tight_layout()
    return plt

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
st.markdown("""
<h1 style="text-align:center;">🔍 Buscador de Providencias</h1>
<h3 style="text-align:center; color:#9CA3AF;">MongoDB + Neo4j + Similitudes</h3>
""", unsafe_allow_html=True)

# =============================================
# SIDEBAR
# =============================================
st.sidebar.header("Filtros de búsqueda")

input_providencia = st.sidebar.text_input("Número de providencia", placeholder="Ej: T-123-23")
input_tipo = st.sidebar.text_input("Tipo de providencia", placeholder="Ej: Tutela")
input_keywords = st.sidebar.text_input("Palabras clave", placeholder="Ej: ministerio")

buscar = st.sidebar.button("Buscar")

# GRAFO MANUAL
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
        st.markdown("<div class='graph-box'>", unsafe_allow_html=True)
        fig = crear_grafo(sims, highlight=grafo_nombre)
        st.pyplot(fig)
        st.markdown("</div>", unsafe_allow_html=True)

# =============================================
# CONSULTAS MONGO
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
# EJECUTAR CONSULTA
# =============================================
if buscar:
    query = armar_query(input_providencia, input_tipo, input_keywords)
    st.write("### Query generada:")
    st.code(str(query))

    resultados = list(collection.find(query))
    st.write(f"### Resultados ({len(resultados)})")

    if len(resultados) == 0:
        st.info("No se encontraron documentos.")

    # GRAFO FILTRADO
    if input_tipo or input_keywords:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Grafo de providencias filtradas (NetworkX)")

        sims = obtener_grafo_desde_lista(resultados)

        if len(sims) == 0:
            st.info("No hay relaciones de similitud.")
        else:
            st.markdown("<div class='graph-box'>", unsafe_allow_html=True)
            fig = crear_grafo(sims)
            st.pyplot(fig)
            st.markdown("</div>", unsafe_allow_html=True)

    # MOSTRAR DOCUMENTOS
    for doc in resultados:
        prov = doc.get("providencia")

        with st.expander(f"Providencia: {prov} | Tipo: {doc.get('tipo', 'N/A')}"):

            doc_mostrar = doc.copy()
            doc_mostrar["Texto"] = truncar_texto(doc.get("Texto", ""), 300)
            st.write(doc_mostrar)

            sims = obtener_similitudes(prov)

            if len(sims) == 0:
                st.info("Esta providencia no tiene relaciones.")
            else:
                st.subheader("Listado de similitudes")
                for r in sims:
                    destino = r["destino"]
                    score = r["similitud"]
                    st.write(f"- **{destino}** → similitud: **{score}**")
