import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np
import os
import pandas as pd

class ChromaAgent:
    def __init__(self, db_dir="new_support_issues", collection_name="new_support_issues"):
        """
        Initialize the ChromaDB agent.
        
        Args:
            db_dir (str): Directory path for ChromaDB
            collection_name (str): Name of the ChromaDB collection
        """
        # Create the directory if it doesn't exist
        os.makedirs(db_dir, exist_ok=True)
            
        self.db_dir = db_dir
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(path=db_dir)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        
        # Get or create collection
        collections = [c.name for c in self.client.list_collections()]
        print(f"Available collections: {collections}")
        
        if collection_name in collections:
            self.collection = self.client.get_collection(name=collection_name)
            try:
                count = self.collection.count()
                print(f"Collection '{collection_name}' contains {count} documents")
            except Exception as e:
                print(f"Error getting collection count: {str(e)}")
        else:
            self.collection = self.client.create_collection(name=collection_name)
            print(f"Created new collection '{collection_name}'")
            
    def load_data_from_csv(self, csv_path = "chat_history/historical_ticket_new.csv"):
        """
        Load data from CSV and add to ChromaDB.
        
        Args:
            csv_path (str): Path to the CSV file
        """
        try:
            # Use absolute path for CSV if provided with relative path
            if not os.path.isabs(csv_path):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                full_path = os.path.join(base_dir, csv_path)
                if os.path.exists(full_path):
                    csv_path = full_path
                    print(f"Using absolute path: {csv_path}")
            
            if not os.path.exists(csv_path):
                print(f"CSV file not found at: {csv_path}")
                return 0
                
            df = pd.read_csv(csv_path)
            print(f"Loaded CSV with {len(df)} rows")
            past_issues = []
            
            for index, row in df.iterrows():
                past_issues.append({
                    "id": str(row['Ticket_ID']),  # Ensure ID is a string
                    "issue_summary": row['Issue_Category'],
                    "solution": row['Solution'],
                    "ticket_open_date": row['Ticket_Open_Date'],
                    "resolution_date": row['Date_of_Resolution'],
                    "assigned_team": row['Assigned_To_Team']
                })
                
            if not past_issues:
                print("No issues found in CSV file")
                return 0
                
            # Embed and add to Chroma
            texts = [item["issue_summary"] for item in past_issues]
            print(f"Embedding {len(texts)} texts")
            embeddings = self.embedder.encode(texts).tolist()
            
            metadatas = [{
                "solution": item["solution"],
                "ticket_open_date": item["ticket_open_date"],
                "resolution_date": item["resolution_date"],
                "assigned_team": item["assigned_team"]
            } for item in past_issues]
            
            ids = [item["id"] for item in past_issues]
            
            # Check if collection already has data
            try:
                before_count = self.collection.count()
                print(f"Collection already has {before_count} documents before adding")
            except Exception as e:
                print(f"Error checking document count: {str(e)}")
                before_count = 0
            
            # Add documents to collection
            self.collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            # Verify documents were added
            try:
                after_count = self.collection.count()
                print(f"Collection now has {after_count} documents after adding")
                added = after_count - before_count
                print(f"Added {added} new documents")
            except Exception as e:
                print(f"Error checking document count after adding: {str(e)}")
                added = len(past_issues)
            
            return added
        
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            return 0
    
    def query(self, query_text, n_results=3):
        """
        Query ChromaDB for similar issues.
        
        Args:
            query_text (str): The text to search for
            n_results (int): Number of similar results to return
            
        Returns:
            list: List of dictionaries containing similar issues with their metadata
        """
        print(f"Querying ChromaDB for: '{query_text}'")
        
        # Ensure we have something to query
        try:
            count = self.collection.count()
            print(f"Collection has {count} documents")
            if count == 0:
                print("WARNING: No documents in collection to query")
                return []
        except Exception as e:
            print(f"Error checking collection count: {str(e)}")
            # If can't determine count, proceed with query anyway
        
        # Create embedding for the query
        query_embedding = self.embedder.encode(query_text).tolist()
        
        # Query the collection - ensure n_results is at least 1
        n_results = max(1, n_results)
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Check if results are valid
            if not results or not results['documents'] or not results['documents'][0]:
                print("Query returned no results")
                return []
                
            print(f"Query returned {len(results['documents'][0])} results")
            
            # Organize results
            organized_results = []
            for i in range(len(results['documents'][0])):
                # Convert distance to similarity score using exponential decay
                similarity = np.exp(-results['distances'][0][i])
                
                result = {
                    'issue': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'similarity_score': round(similarity, 2)  # Round to 2 decimal places
                }
                organized_results.append(result)
                
                print(f"Result #{i+1}: '{result['issue']}' - Score: {result['similarity_score']}")
            
            return organized_results
        except Exception as e:
            print(f"ERROR during query: {str(e)}")
            return [] 