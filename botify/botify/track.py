import itertools
import json
import pickle
from dataclasses import dataclass, field
from typing import List


@dataclass
class Track:
    track: int
    artist: str
    title: str
    recommendations: List[int] = field(default=lambda: [])


class Catalog:
    """
    A helper class used to load track data upon server startup
    and store the data to redis.
    """

    def __init__(self, app):
        self.app = app
        self.tracks = []
        self.top_tracks = []
        # другие топы
        self.top_tracks_random = []
        self.top_tracks_collaborative = []
        self.top_tracks_contextual = []
        self.top_tracks_top_pop = []
        self.top_tracks_sticky_artist = []

    #DONE Добавить поддержку загрузки других файлов топов по популярности
    def load(self, catalog_path, 
             top_tracks_path,
             top_tracks_random_path,
             top_tracks_collaborative_path,
             top_tracks_contextual_path,
             top_tracks_sticky_artist_path,
             top_tracks_top_pop_path):

        self.app.logger.info(f"Loading tracks from {catalog_path}")
        with open(catalog_path) as catalog_file:
            for j, line in enumerate(catalog_file):
                data = json.loads(line)
                self.tracks.append(Track(data["track"], data["artist"], data["title"], data["recommendations"]))
        self.app.logger.info(f"Loaded {j+1} tracks")
        
        #DONE Сделать цикл обхода путей для загрузки файлов
        top_tracks_paths_list = [top_tracks_path, 
                                 top_tracks_random_path,
                                 top_tracks_collaborative_path,
                                 top_tracks_contextual_path,
                                 top_tracks_sticky_artist_path,
                                 top_tracks_top_pop_path] 
        self_top_attr = ['top_tracks',
                          'top_tracks_random',
                          'top_tracks_collaborative',
                          'top_tracks_contextual',
                          'top_tracks_sticky_artist',
                          'top_tracks_top_pop']
        for path, self_attr in zip(top_tracks_paths_list, self_top_attr):
            self.app.logger.info(f"Loading top tracks from {path}")
            with open(path) as top_tracks_file:
                self.__dict__[self_attr] = json.load(top_tracks_file)
            self.app.logger.info(f"Loaded {len(self.__dict__[self_attr])} top tracks")
        return self
        
        # self.app.logger.info(f"Loading top tracks from {top_tracks_path}")
        # with open(top_tracks_path) as top_tracks_file:
        #     self.top_tracks = json.load(top_tracks_file)
        # self.app.logger.info(f"Loaded {len(self.top_tracks)} top tracks")
        # return self

    def upload_tracks(self, redis):
        self.app.logger.info(f"Uploading tracks to redis")
        for track in self.tracks:
            redis.set(track.track, self.to_bytes(track))
        self.app.logger.info(f"Uploaded {len(self.tracks)} tracks")

    def upload_artists(self, redis):
        self.app.logger.info(f"Uploading artists to redis")
        sorted_tracks = sorted(self.tracks, key=lambda t: t.artist)
        for j, (artist, artist_catalog) in enumerate(
                itertools.groupby(sorted_tracks, key=lambda t: t.artist)
        ):
            artist_tracks = [t.track for t in artist_catalog]
            redis.set(artist, self.to_bytes(artist_tracks))
        self.app.logger.info(f"Uploaded {j + 1} artists")

    def upload_recommendations(self, redis):
        self.app.logger.info(f"Uploading recommendations to redis")
        recommendations_file_path = self.app.config["RECOMMENDATIONS_FILE_PATH"]
        with open(recommendations_file_path) as recommendations_file:
            for j, line in enumerate(recommendations_file):
                recommendations = json.loads(line)
                redis.set(
                    recommendations["user"], self.to_bytes(recommendations["tracks"])
                )
        self.app.logger.info(f"Uploaded recommendations for {j + 1} users")

    def to_bytes(self, instance):
        return pickle.dumps(instance)

    def from_bytes(self, bts):
        return pickle.loads(bts)
