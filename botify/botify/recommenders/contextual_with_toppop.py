from collections import Counter
from typing import List
from .random import Random
from .recommender import Recommender
import random

#DONE Добавить подержку запоминания уже прослушанных треков
#DONE Добавить использование топа вместо нейросетевого рекомендера при снижении интереса
#DONE Добавить фильтр по истории прослушанных треков
#DONE Добавить фильтр по истории и исполнитлю (если в истории больше чем n песен данного исполнителя фильтровать их)

class Contextual_with_toppop(Recommender):
    """
    Recommend tracks closest to the previous one.
    Fall back to the TopPop recommender if bad previous 
    track time or no recommendations found for the track.
    Fall back to the Random if recommendations list empty
    after filtering. 
    """
    
    def __init__(self, tracks_redis, history_redis, catalog, history, 
                 recommender_tolerance: float = 0.8, 
                 toppoplen: int = 100, 
                 filter_strategy: str = "SIMPLE_HISTORY",
                 artist_tolerance: int = 3):
        """
        Initialization
        Args:
            tracks_redis (Redis): Tracks data on redis
            history_redis (Redis): User history data on redis
            history (History): Functions for write/read history
            catalog (Catalog): For top data and some functions
            recommender_tolerance (float, optional): If prev track time below this value use TopPop. 
            Defaults to 0.8.
            toppoplen (int, optional): Length of top in TopPop. Defaults to 100.
            filter_strategy (str, optional): Filter strategy. Defaults to "SIMPLE_HISTORY".
                SIMPLE_HISTORY: Filter tracks in history
                AUTHOR_TRACK_HISTORY: Filter tracks if they were in history or author has met
                more than n times.
        Self:
            fallback: TopPop
            second_fallback: Random
        """
        self.tracks_redis = tracks_redis
        self.fallback = catalog.top_tracks_collaborative[:toppoplen]
        self.second_fallback = Random(tracks_redis)
        self.catalog = catalog
        self.history = history
        self.rec_tolerance = recommender_tolerance
        self.history_redis = history_redis
        self.filter_strategy = filter_strategy
        self.artist_tolerance = artist_tolerance

    def recommend_next(self, user: int, prev_track: int, prev_track_time: float) -> int:
        self.history.append_item(self.history_redis, user, prev_track)
        session_history = self.history.get(self.history_redis, user)
        
        previous_track = self.tracks_redis.get(prev_track)
        if previous_track is None:
            # Use TopPop
            recommendations = list(self.fallback)
            #Filter
            filtered_recommendations = self.filter(recommendations, session_history, self.filter_strategy)
            if len(filtered_recommendations) == 0:
                # Use Random
                return self.second_fallback.recommend_next(user, prev_track, prev_track_time)
            else:
                return self.shuffled(filtered_recommendations)
            
        previous_track = self.catalog.from_bytes(previous_track)
        recommendations = previous_track.recommendations
        if recommendations is None or prev_track_time < self.rec_tolerance:
            # Use TopPop
            recommendations = list(self.fallback)
            #Filter
            filtered_recommendations = self.filter(recommendations, session_history, self.filter_strategy)
            if len(filtered_recommendations) == 0:
                # Use Random
                return self.second_fallback.recommend_next(user, prev_track, prev_track_time)
            else:
                return self.shuffled(filtered_recommendations)
        
        #Filter contextual
        filtered_recommendations = self.filter(recommendations, session_history, self.filter_strategy)
        if len(filtered_recommendations) == 0:
            
            # Use TopPop
            recommendations = list(self.fallback)
            filtered_recommendations = self.filter(recommendations, session_history, self.filter_strategy)
            if len(filtered_recommendations) == 0:
                # Use Random
                return self.second_fallback.recommend_next(user, prev_track, prev_track_time)
            else:
                return self.shuffled(filtered_recommendations)
            
        else:
            # Contextual
            return self.shuffled(filtered_recommendations)
    
    def shuffled(self, recommendations: List[int]) -> int:
        shuffled = list(recommendations)
        random.shuffle(shuffled)
        return shuffled[0]
        
    def filter(self, recommendations, session_history, filter_strategy :str):
        if filter_strategy == "SIMPLE_HISTORY":
            return list(set(recommendations) - set(session_history))
        if filter_strategy == "AUTHOR_TRACK_HISTORY":
            # step 1 filter history
            history_filtered_recommendations = list(set(recommendations) - set(session_history))
            # step 2 create artist history dict
            artists = []
            for track_id in session_history:
                history_track = self.tracks_redis.get(track_id)
                history_track = self.catalog.from_bytes(history_track)
                artists.append(history_track.artist)
            artists_dict = Counter(artists)
            # step 3 iterate throught history_filtered_recommendations
            final_recommendations = []
            for track_id in history_filtered_recommendations:
                the_track = self.tracks_redis.get(track_id)
                the_track = self.catalog.from_bytes(the_track)
                if artists_dict[the_track.artist] > self.artist_tolerance:
                    pass
                else:
                    final_recommendations.append(track_id)
            return final_recommendations
        