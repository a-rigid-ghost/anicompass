import chromadb

from constants import *

def get_similar_anime(anime_id, collection: chromadb.Collection):
    query_embedding = collection.get(ids=[anime_id], include=["embeddings"])["embeddings"][0]
    return collection.query(query_embeddings=query_embedding, n_results=10)["metadatas"]

def main():
    client = chromadb.PersistentClient(path=CHROMADB_PERSISTENCE_PATH)
    anime_collection = client.get_collection(name=ANIME_COLLECTION_NAME)
    print(get_similar_anime('7054', anime_collection))

main()