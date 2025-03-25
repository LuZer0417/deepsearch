'''
input: inverted_index_XXX.json files (where XXX represents the starting letter of terms)
output: MongoDB database with multiple collections (inverted_index_XXX)
'''

import json
import os
from pymongo import MongoClient
from tqdm import tqdm  # Used for progress bar

def process_distributed_files(directory_path):
    """
    Process all distributed inverted index files in the directory, each file corresponds to a MongoDB collection
    :param directory_path: Path to directory containing inverted index files
    """
    # Connect to MongoDB
    client = MongoClient('mongodb://35.214.111.75:27017')
    db = client['search_db']
    
    # Get all inverted index files
    files = [f for f in os.listdir(directory_path) 
             if f.startswith('inverted_index_') and f.endswith('.json')]
    
    print(f"Found {len(files)} inverted index files")
    
    # Process each file
    for filename in files:
        # Get collection name suffix from filename (e.g.: inverted_index_a.json -> a)
        collection_suffix = filename.replace('inverted_index_', '').replace('.json', '')
        collection_name = f'inverted_index_{collection_suffix}'
        
        print(f"\nProcessing file: {filename}")
        print(f"Corresponding collection: {collection_name}")
        
        # Get or create corresponding collection
        collection = db[collection_name]
        
        # Empty existing collection (optional)
        collection.drop()
        
        file_path = os.path.join(directory_path, filename)
        try:
            # Load JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            total_terms = len(data)
            print(f"File contains {total_terms} terms")
            
            # Batch insert data
            batch_size = 1000
            batch = []
            processed_terms = 0
            
            with tqdm(total=total_terms, desc="Processing progress") as pbar:
                for term, term_data in data.items():
                    batch.append({
                        "term": term,
                        "data": term_data
                    })
                    
                    if len(batch) >= batch_size:
                        collection.insert_many(batch)
                        processed_terms += len(batch)
                        pbar.update(len(batch))
                        batch = []
                
                # Insert remaining data
                if batch:
                    collection.insert_many(batch)
                    processed_terms += len(batch)
                    pbar.update(len(batch))
            
            # Create index for each collection
            print(f"Creating index for collection {collection_name}...")
            collection.create_index("term")
            
            print(f"Successfully processed {processed_terms} terms")
            
        except Exception as e:
            print(f"Error processing file {filename}: {str(e)}")
    
    print("\nAll database collections built!")
    
    # Print all created collections
    collections = db.list_collection_names()
    inverted_index_collections = [c for c in collections if c.startswith('inverted_index_')]
    print("\nCreated inverted index collections:")
    for collection in sorted(inverted_index_collections):
        count = db[collection].count_documents({})
        print(f"- {collection}: {count} terms")

if __name__ == "__main__":
    # Specify directory containing inverted index files
    directory = "/Users/luzer/Downloads/inverted_index"  # Replace with your directory path
    process_distributed_files(directory)