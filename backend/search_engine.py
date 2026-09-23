import os
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# Initialize SentenceTransformer for local embeddings
# all-MiniLM-L6-v2 is a small, fast model (the same one used by default in ChromaDB)
model = SentenceTransformer('all-MiniLM-L6-v2')

def index_all_accounts(db_connection_function):
    """Pulls live data fields out of MySQL, structures them conceptually, and stores vector embeddings in Supabase."""
    if not supabase:
        print("[WARNING] Supabase client not initialized. Skipping indexing.")
        return

    connection = db_connection_function()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT account_id, name, company, source, status FROM accounts")
        records = cursor.fetchall()
        
        for record in records:
            # Build a rich string context that captures the data's meaning
            context_string = f"Account representing {record['name']} working at {record['company'] or 'unknown company'}. Status in sales funnel is {record['status']}, sourced via {record['source']}."
            
            # Generate embedding vector
            embedding = model.encode(context_string).tolist()
            
            # Upsert into Supabase pgvector table
            supabase.table('accounts_vectors').upsert({
                "account_id": record['account_id'],
                "name": record['name'],
                "embedding": embedding
            }, on_conflict="account_id").execute()
            
        print("Vector database embedding synchronizations to Supabase completed successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to index accounts: {e}")
    finally:
        cursor.close()
        connection.close()

def semantic_search_pipeline(query_text, num_results=3):
    """Executes a vector distance query via Supabase RPC to pull contextually matching profiles."""
    if not supabase:
        print("[WARNING] Supabase client not initialized. Returning empty.")
        return []

    try:
        # Generate embedding for the search query
        query_embedding = model.encode(query_text).tolist()
        
        # Call the Supabase RPC function for vector matching
        response = supabase.rpc('match_accounts', {
            'query_embedding': query_embedding,
            'match_threshold': 0.3,
            'match_count': num_results
        }).execute()
        
        # Extract matching account IDs
        return [match['account_id'] for match in response.data]
    except Exception as e:
        print(f"[ERROR] Supabase semantic search failed: {e}")
        return []