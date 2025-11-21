import streamlit as st
from pymongo import MongoClient

# =============================================
# 1. CONEXIÓN A MONGODB
# =============================================
# Ajusta tu cadena de conexión
MONGO_URI = "mongodb+srv://superuser:ynmkEGkQ4JPPs9sI@cluster0.qfgghrp.mongodb.net/?appName=Cluster0"
DB_NAME = "Proyecto_Final"
COLLECTION_NAME = "Audios_Sentencias"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# =============================================
# 2. TÍTULO DE APLICACIÓN
# =============================================
st.title("Buscador de Providencias en MongoDB")
st.write("Aplicación para buscar por providencia, tipo y palabras clave en el texto.")

# =============================================
# 3. SIDEBAR DE FILTROS
# =============================================
st.sidebar.header("Filtros de búsqueda")


input_providencia = st.sidebar.text_input("Número de providencia")
input_tipo = st.sidebar.text_input("Tipo de providencia")
input_keywords = st.sidebar.text_input("Palabras clave en el campo 'texto' (separadas por coma)")


buscar = st.sidebar.button("Buscar")


# =============================================
# 4. ARMAR QUERY
# =============================================
# =============================================
# 4. ARMAR CONSULTAS INDIVIDUALES
# =============================================
def consulta_por_providencia(nombre):
    return {"providencia": nombre} if nombre else {}


def consulta_por_tipo(tipo):
    return {"tipo": tipo} if tipo else {}


def consulta_por_palabras(keywords):
    if not keywords:
        return {}
    palabras = [p.strip() for p in keywords.split(",") if p.strip()]
    return {"texto": {"$regex": "|".join(palabras), "$options": "i"}}
# =============================================
# 5. COMBINAR CONSULTAS SI ES NECESARIO
# =============================================
def armar_query(providencia, tipo, keywords):
    query = {}
    query.update(consulta_por_providencia(providencia))
    query.update(consulta_por_tipo(tipo))
    query.update(consulta_por_palabras(keywords))
    return query


# =============================================
# 5. EJECUTAR CONSULTA
# =============================================
if buscar:
    query = armar_query(input_providencia, input_tipo, input_keywords)
    st.write("### Query generada:")
    st.code(str(query))
    resultados = list(collection.find(query))
    st.write(f"### Resultados ({len(resultados)})")
    if len(resultados) == 0:
        st.info("No se encontraron documentos.")
    else:
        for doc in resultados:
            with st.expander(f"Providencia: {doc.get('providencia', 'N/A')} - Tipo: {doc.get('tipo', 'N/A')}"):
                st.write(doc)