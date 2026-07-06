import chromadb
from chromadb.utils import embedding_functions
import mysql.connector

# Initialize a persistent, local system vector database file space
chroma_client = chromadb.PersistentClient(path="./chroma_db_storage")
# Use a lightweight, local default mathematical text embedding model
default_ef = embedding_functions.DefaultEmbeddingFunction()

collection = chroma_client.get_or_create_collection(
    name="crm_accounts_vectors", 
    embedding_function=default_ef
)

def index_all_accounts(db_connection_function):
    """Pulls live data fields out of MySQL, structures them conceptually, and stores vector embeddings."""
    connection = db_connection_function()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT account_id, name, company, source, status FROM accounts")
        records = cursor.fetchall()
        
        for record in records:
            # Build a rich string context that captures the data's meaning
            context_string = f"Account representing {record['name']} working at {record['company'] or 'unknown company'}. Status in sales funnel is {record['status']}, sourced via {record['source']}."
            
            # Upsert directly into the local vector space store
            collection.upsert(
                documents=[context_string],
                metadatas=[{"account_id": record['account_id'], "name": record['name']}],
                ids=[str(record['account_id'])]
            )
        print("Vector database embedding synchronizations completed successfully.")
    finally:
        cursor.close()
        connection.close()

def semantic_search_pipeline(query_text, num_results=3):
    """Executes a geometric vector distance query to pull contextually matching profiles."""
    results = collection.query(
        query_texts=[query_text],
        n_results=num_results
    )
    # Extract structural match accounts
    return [int(uid) for uid in results['ids'][0]]