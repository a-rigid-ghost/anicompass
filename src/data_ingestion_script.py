import csv
from pathlib import Path

import chromadb

from constants import *

CHROMA_MAX_BATCH_SIZE = 5000
RELATIVE_WEIGHT_COLLABORATIVE_EMBEDDING = 2.5

base_path = Path(__file__).parent
ANIME_DATASET_FILEPATH = (base_path / "../data/anime_dataset.csv").resolve()
COLLABORATIVE_EMBEDDINGS_FILEPATH = (base_path / "../data/collaborative_filtering_embeddings.csv").resolve()
CONTENT_EMBEDDINGS_FILEPATH = (base_path / "../data/content_based_embeddings.csv").resolve()


def read_csv(filepath):
    result = {}
    with open(filepath, mode='r', encoding="utf8") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            item = {}
            for k,v in row.items():
                if k and k != ANIME_ID_KEY:
                    item[k] = v
            result[str(row[ANIME_ID_KEY])] = item
    return result
            

def get_merged_dataset(anime_dataset_dict, collaborative_embedding, content_embedding):
    result = {}
    for anime_id, anime_attrs in anime_dataset_dict.items():
        if anime_id not in collaborative_embedding:
            continue
        item = {}
        item[ANIME_METADATA_KEY] = {
            NAME_KEY: str(anime_attrs[NAME_KEY]),
            ENGLISH_NAME_KEY: str(anime_attrs[ENGLISH_NAME_KEY]),
            IMAGE_URL_KEY: str(anime_attrs[IMAGE_URL_KEY]),
            POPULARITY_KEY: int(float(anime_attrs[POPULARITY_KEY])),
            FAVOURITE_KEY: int(float(anime_attrs[FAVOURITE_KEY])),
            MEMBERS_KEY: int(float(anime_attrs[MEMBERS_KEY])),
        }
        item[COLLABORATIVE_EMBEDDINGS_KEY] = [float(v) for k, v in collaborative_embedding[anime_id].items()]
        item[CONTENT_EMBEDDINGS_KEY] = [float(v) for k, v in content_embedding[anime_id].items()]
        result[anime_id] = item
    print(f"The merged dataset has {len(result)} animes.")
    return result


def get_merged_embedding(collaborative_embedding, content_embedding):
    weighted_collaborative = [RELATIVE_WEIGHT_COLLABORATIVE_EMBEDDING * w for w in collaborative_embedding]
    return weighted_collaborative + content_embedding


def ingest_data_into_collection(merged_dataset, collection: chromadb.Collection):
    embeddings_list = []
    metadata_list = []
    ids_list = []
    for anime_id, anime_attrs in merged_dataset.items():
        ids_list.append(anime_id)
        metadata_list.append(anime_attrs[ANIME_METADATA_KEY])
        embeddings_list.append(get_merged_embedding(anime_attrs[COLLABORATIVE_EMBEDDINGS_KEY], anime_attrs[CONTENT_EMBEDDINGS_KEY]))
    for start_idx in range(0, len(merged_dataset), CHROMA_MAX_BATCH_SIZE):
        end_idx = min(start_idx + CHROMA_MAX_BATCH_SIZE, len(merged_dataset))
        collection.add(
            ids=ids_list[start_idx: end_idx],
            embeddings=embeddings_list[start_idx: end_idx],
            metadatas=metadata_list[start_idx: end_idx]
        )
    print("Data Ingestion Complete")


def main():
    anime_dataset_dict = read_csv(ANIME_DATASET_FILEPATH)
    collaborative_embedding = read_csv(COLLABORATIVE_EMBEDDINGS_FILEPATH)
    content_embedding = read_csv(CONTENT_EMBEDDINGS_FILEPATH)

    merged_dataset = get_merged_dataset(anime_dataset_dict=anime_dataset_dict, 
                                        collaborative_embedding=collaborative_embedding, 
                                        content_embedding=content_embedding)

    client = chromadb.PersistentClient(path=CHROMADB_PERSISTENCE_PATH)
    anime_collection = client.create_collection(name=ANIME_COLLECTION_NAME)
    ingest_data_into_collection(merged_dataset=merged_dataset, collection=anime_collection)


main()