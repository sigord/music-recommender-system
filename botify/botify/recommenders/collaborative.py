import random
from .random import Random
from .recommender import Recommender


class Collaborative(Recommender):
    def __init__(self, recommendations_redis, track_redis, catalog):
        self.recommendations_redis = recommendations_redis
        self.fallback = Random(track_redis)
        self.catalog = catalog

    def recommend_next(self, user: int, prev_track: int, prev_track_time: float) -> int:
        recommendations = self.recommendations_redis.get(user)
        if recommendations is not None:
            shuffled = list(self.catalog.from_bytes(recommendations))
            random.shuffle(shuffled)
            return shuffled[0]
        else:
            return self.fallback.recommend_next(user, prev_track, prev_track_time)