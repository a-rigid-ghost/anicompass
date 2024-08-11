import os
import requests
import logging
import re

from constants import *
from models import Anime, User, UserAnimeRating

import chromadb
import numpy as np
from jikanpy import Jikan
from dotenv import load_dotenv
from ratelimit import limits, RateLimitException
from backoff import on_exception, expo

load_dotenv()


class VectorDB:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMADB_PERSISTENCE_PATH)
        self.anime_colection = self.client.get_collection(name=ANIME_COLLECTION_NAME)
    
    def get_anime_embedding(self, anime_id):
        result = None
        try:
            result = self.anime_colection.get(ids=[anime_id], include=["embeddings"])["embeddings"][0]
        except IndexError:
            logging.warn(f"Anime: {anime_id} does not exist in ChromaDB")
        return result
    
    def get_similar_animes_by_embedding(self, query_embedding, topk = 10):
        response = self.anime_colection.query(query_embeddings=query_embedding, n_results=topk)
        result = {}
        if response is not None:
            for idx, anime_id in enumerate(response['ids'][0]):
                metadata_item = response['metadatas'][0][idx]
                result[anime_id] = Anime(
                    mal_id=anime_id,
                    title=metadata_item[NAME_KEY],
                    english_title=metadata_item[ENGLISH_NAME_KEY],
                    image_url=metadata_item[IMAGE_URL_KEY],
                    popularity=metadata_item[POPULARITY_KEY],
                    favourites=metadata_item[FAVOURITE_KEY],
                    members=metadata_item[MEMBERS_KEY]
                )
        return result
    
    def get_similar_animes(self, anime_id, topk = 10):
        query_embedding = self.get_anime_embedding(anime_id=anime_id)
        response = self.anime_colection.query(query_embeddings=query_embedding, n_results=10)
        return self.get_similar_animes_by_embedding(query_embedding=query_embedding, topk=topk)


class JikanAdapter:
    def __init__(self):
        self.jikan = Jikan()
    
    @on_exception(expo, RateLimitException, max_tries=5)
    @limits(calls=1, period=1)
    def get_anime_details(self, anime_id):
        result = self.jikan.anime(id=anime_id, extension='full')["data"]
        return Anime(
            mal_id=str(result["mal_id"]),
            title=result["title"],
            english_title=result["title_english"],
            image_url=result["images"]["jpg"]["large_image_url"],
            popularity=result["popularity"],
            favourites=result["favorites"],
            members=result["members"]
        )
    
    def get_anime_recommendations(self, anime_id, topk=3):
        result = self.jikan.anime(id=anime_id, extension='recommendations')["data"]
        recommended_animes = []
        for recommendation in result[0: topk]:
            recommended_animes.append(self.get_anime_details(recommendation["entry"]["mal_id"]))
        return recommended_animes


class MalAdapter:
    def __init__(self):
        self.base_url = "https://api.myanimelist.net/v2/"
        self.client_id = os.getenv('MAL_CLIENT_ID')

        if not self.client_id:
            raise ValueError("Your MAL_CLIENT_ID is not set in the .env file")
        
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-MAL-CLIENT-ID': self.client_id
        }
    
    def call(self, uri, method="get", params=None, *args, **kwargs):
        requester = getattr(requests, method.lower())
        url = self.base_url + uri
        response = requester(url=url,
                             headers=self.headers,
                             params=params,
                             *args,
                             **kwargs)
        response_json = response.json()
        return response_json

    
    def  get_user_anime_list(self, username):
        uri = f"users/{username}/animelist"
        query_params = {
            "fields": "list_status",
            "limit": 100
        }
        result = self.call(uri=uri, method="get", params=query_params)["data"]
        user_anime_list = []
        for rating in result:
            user_anime_list.append(UserAnimeRating(
                mal_id=str(rating["node"]["id"]),
                score=int(rating["list_status"]["score"]),
                status=str(rating["list_status"]["status"])
            ))
        return user_anime_list


class RecFactory:

    def __init__(self, username):
        self.vector_engine = VectorDB()
        self.mal_client = MalAdapter()
        self.jikan_client = JikanAdapter()
        self._build_user_persona(username=username)
    
    def _build_user_persona(self, username):
        self.user = User(username=username, rating_history=self.mal_client.get_user_anime_list(username=username))
        self.already_watched = {}
        for user_anime in self.user.rating_history:
            if user_anime.status in ['watching', 'completed', 'on_hold', 'dropped']:
                self.already_watched[user_anime.mal_id] = user_anime
        self._clean_ratings_by_status('watching')
        self._clean_ratings_by_status('completed')
        self._clean_ratings_by_status('on_hold')
        self._clean_ratings_by_status('dropped', 0)
        self._normalise_user_anime_ratings()
    
    def _clean_ratings_by_status(self, status, default_rating=None):
        if not default_rating:
            rating_sum = 0
            rating_count = 0
            for _, user_anime in self.already_watched.items():
                if user_anime.status == status:
                    rating_count += 1
                    rating_sum += user_anime.score
            
            try:
                default_rating = rating_sum / rating_count
            except ZeroDivisionError:
                default_rating = 0

        
        for _, user_anime in self.already_watched.items():
            if user_anime.status == status and user_anime.score == 0:
                user_anime.score = default_rating
    
    
    def _rating_scaler(self, rating):
        RATING_MIN = 0
        RATING_MAX = 10
        RATING_MID = (RATING_MAX + RATING_MIN)/2
        RATING_SCALE = (RATING_MAX - RATING_MIN)/2
        return (rating - RATING_MID)/RATING_SCALE
    
    def _normalise_user_anime_ratings(self):
        
        user_rating_sum = 0
        user_rating_count = 0
        for _, user_anime in self.already_watched.items():
            user_anime.score = self._rating_scaler(user_anime.score)
            user_rating_sum += user_anime.score
            user_rating_count += 1
        self.user_avg_rating = user_rating_sum / user_rating_count
    
    def generate_anime_recommendations(self, topk):
        SEARCH_EXPANSION_MULTIPLIER = 5
        self.animes_in_db = {}
        self.animes_not_in_db = set()
        for anime_id in self.already_watched.keys():
            anime_embedding = self.vector_engine.get_anime_embedding(anime_id=anime_id)
            if anime_embedding:
                self.animes_in_db[anime_id] = anime_embedding
            else:
                self.animes_not_in_db.add(anime_id)
        self.anime_rec_list = self._dedup_animes([
            *self._get_anime_recommendations_based_on_user_profile(topk=topk*SEARCH_EXPANSION_MULTIPLIER),
        ])
        return self._rank_animes_by_popularity(self.anime_rec_list)[0: topk]

    def _get_anime_recommendations_based_on_user_profile(self, topk):
        weights_array = [self.already_watched[anime_id].score for anime_id in self.animes_in_db.keys()]
        weights_array = weights_array / np.linalg.norm(weights_array)
        weighted_avg = np.average(
            [np.array(v) for v in self.animes_in_db.values()], weights=weights_array, axis=0
        )
        self.user_profile = weighted_avg.tolist()
        anime_rec = self.vector_engine.get_similar_animes_by_embedding(self.user_profile, topk=topk)
        polished_rec = self._polish_recommendations(self._filter_already_watched_animes(list(anime_rec.values())))
        return polished_rec
    
    def _get_anime_recommendations_for_external_animes(self, external_anime_ids):
        external_recs = []
        for anime_id in external_anime_ids:
            external_recs.extend(self.jikan_client.get_anime_recommendations(anime_id=anime_id))
        external_recs = self._filter_already_watched_animes(external_recs)
        return external_recs
    
    def _polish_recommendations(self, anime_list: list[Anime]):
        anime_list = self._dedup_animes(anime_list=anime_list)
        primary_anime_list, secondary_anime_list = self._filter_secondary_animes(anime_list=anime_list)
        secondary_anime_neighbours = []
        for anime in secondary_anime_list:
            secondary_anime_neighbours.extend(
                self._rank_animes_by_members(
                    list(self.vector_engine.get_similar_animes(anime_id=anime.mal_id, topk=10).values())
                )[0: 3]
            )
        new_primary_anime_list, _ = self._filter_secondary_animes(anime_list=secondary_anime_neighbours)
        primary_anime_list.extend(new_primary_anime_list)
        return self._filter_already_watched_animes(self._dedup_animes(primary_anime_list))

    def _rank_animes_by_members(self, anime_list: list[Anime]):
        return sorted(anime_list, key=lambda x: x.members, reverse=True)
    
    def _rank_animes_by_popularity(self, anime_list: list[Anime]):
        return sorted(anime_list, key=lambda x: x.popularity, reverse=False)
    
    def _filter_already_watched_animes(self, anime_list: list[Anime]):
        return [anime for anime in anime_list if anime.mal_id not in self.already_watched]
    
    def _filter_secondary_animes(self, anime_list: list[Anime]):
        filter_words = set(["movie", "season", "cour", "film"])
        primary_anime_list = []
        secondary_anime_list = []
        for anime in anime_list:
            title_set = set(word.lower() for word in re.split(',| |:|-|!',anime.english_title))
            common_words = title_set.intersection(filter_words)
            if len(common_words) == 0:
                primary_anime_list.append(anime)
            else:
                secondary_anime_list.append(anime)
        return primary_anime_list, secondary_anime_list
    
    def _dedup_animes(self, anime_list: list[Anime]):
        counted_animes = set()
        dedup_anime_list = []
        for anime in anime_list:
            if anime.mal_id not in counted_animes:
                counted_animes.add(anime.mal_id)
                dedup_anime_list.append(anime)
        return dedup_anime_list    
