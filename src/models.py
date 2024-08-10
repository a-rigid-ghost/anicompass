from dataclasses import dataclass

@dataclass
class Anime:
    mal_id: str
    title: str
    english_title: str
    image_url: str
    popularity: int
    favourites: int
    members: int


@dataclass
class UserAnimeRating:
    mal_id: str
    score: int
    status: str


@dataclass
class User:
    username: str
    rating_history: list[UserAnimeRating]