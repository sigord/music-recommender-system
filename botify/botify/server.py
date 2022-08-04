from distutils.command.config import config
import json
import logging
import time
from dataclasses import asdict
from datetime import datetime

from flask import Flask
from flask_redis import Redis
from flask_restful import Resource, Api, abort, reqparse

from botify.data import DataLogger, Datum
from botify.experiment import Experiments, Treatment
from botify.recommenders.random import Random
from botify.recommenders.sticky_artist import StickyArtist
from botify.recommenders.top_pop import TopPop
from botify.recommenders.contextual import Contextual
from botify.recommenders.collaborative import Collaborative
from botify.track import Catalog

#DONE Добавить новые модули
from botify.history import History
from botify.recommenders.contextual_with_toppop import Contextual_with_toppop

root = logging.getLogger()
root.setLevel("INFO")

app = Flask(__name__)
app.config.from_file("config.json", load=json.load)
api = Api(app)

tracks_redis = Redis(app, config_prefix="REDIS_TRACKS")
artists_redis = Redis(app, config_prefix="REDIS_ARTIST")
recommendations_redis = Redis(app, config_prefix="REDIS_RECOMMENDATIONS")
history_redis = Redis(app, config_prefix="REDIS_USER_HISTORY")

data_logger = DataLogger(app)

#DONE Добавить нужные пути
catalog = Catalog(app).load(app.config["TRACKS_CATALOG"], 
                            app.config["TOP_TRACKS_CATALOG"],
                            app.config["TOP_TRACKS_CATALOG_RANDOM"],
                            app.config["TOP_TRACKS_CATALOG_COLLABORATIVE"],
                            app.config["TOP_TRACKS_CATALOG_CONTEXTUAL"],
                            app.config["TOP_TRACKS_CATALOG_STICKY_ARTIST"],
                            app.config["TOP_TRACKS_CATALOG_TOP_POP"])

catalog.upload_tracks(tracks_redis.connection)
catalog.upload_artists(artists_redis.connection)
catalog.upload_recommendations(recommendations_redis.connection)

parser = reqparse.RequestParser()
parser.add_argument("track", type=int, location="json", required=True)
parser.add_argument("time", type=float, location="json", required=True)

history = History(app)

class Hello(Resource):
    def get(self):
        return {
            "status": "alive",
            "message": "welcome to botify, the best toy music recommender",
        }


class Track(Resource):
    def get(self, track: int):
        data = tracks_redis.connection.get(track)
        if data is not None:
            return asdict(catalog.from_bytes(data))
        else:
            abort(404, description="Track not found")


class NextTrack(Resource):
    def post(self, user: int):
        start = time.time()

        args = parser.parse_args()

        # DONE Спрятать партянку в функцию get_experiment_strategy
        #TODO Don't forget to change the experiment here too
        experiment = Experiments.CONTEXTUAL_COMPARISON
        treatment = experiment.assign(user)
        recommender = ChoseExperimentStrategy(experiment.name).get_experiment_strategy(treatment)

        recommendation = recommender.recommend_next(user, args.track, args.time)

        data_logger.log(
            "next",
            Datum(
                int(datetime.now().timestamp() * 1000),
                user,
                args.track,
                args.time,
                time.time() - start,
                recommendation,
            ),
        )
        return {"user": user, "track": recommendation}


#DONE Добавить возможность вызова структуры экперимента из этого класса        
class ChoseExperimentStrategy:
    def __init__(self, name: str):
        self.name = name
    
    def get_experiment_strategy(self, treatment: Treatment):
        """
        Return recommender class instance
        """
        if self.name == "AA":
            return Random(tracks_redis.connection)
        elif self.name == "STICKY_ARTIST":
            # T1 StickyArtist
            # C Random
            if treatment == Treatment.T1:
                return StickyArtist(tracks_redis.connection, artists_redis.connection, catalog)
            else:
                return Random(tracks_redis.connection)
        elif self.name == "TOP_POP":
            # T1 TopPop with 10 top
            # T2 TopPop with 100 top
            # T3 TopPop with 1000 top
            # C Random
            if treatment == Treatment.T1:
                return TopPop(recommendations_redis.connection, catalog.top_tracks[:10])
            elif treatment == Treatment.T2:
                return TopPop(recommendations_redis.connection, catalog.top_tracks[:100])
            elif treatment == Treatment.T3:
                return TopPop(recommendations_redis.connection, catalog.top_tracks[:1000])
            else:
                return Random(tracks_redis.connection)
        elif self.name == "COLLABORATIVE":
            # T1 Collaborative
            # C Random
            if treatment == Treatment.T1:
                return Collaborative(recommendations_redis.connection, tracks_redis.connection, catalog)
            else:
                return Random(tracks_redis.connection)
        elif self.name == "RECOMMENDERS":
            # T1 Collaborative
            # T2 Contextual
            # T3 StickyArtist
            # T4 TopPop
            # C Random
            if treatment == Treatment.T1:
                return Collaborative(recommendations_redis.connection, tracks_redis.connection, catalog)
            elif treatment == Treatment.T2:
                return Contextual(tracks_redis.connection, catalog)
            elif treatment == Treatment.T3:
                return StickyArtist(tracks_redis.connection, artists_redis.connection, catalog)
            elif treatment == Treatment.T4:
                return TopPop(recommendations_redis.connection, catalog.top_tracks[:100])
            else:
                return Random(tracks_redis.connection)
        #DONE Описать стратегию для экперимента сравнения топ попов с разными данными топов
        elif self.name == "TOP_POP_COMPARISON":
            # T1 TopPop on Random
            # T2 TopPop on StickyArtist
            # T3 TopPop on TopPop
            # T4 TopPop on Collaborative
            # T5 TopPop on Contextual
            # C Random
            if treatment == Treatment.T1:
                return TopPop(recommendations_redis.connection, catalog.top_tracks_random[:100])
            elif treatment == Treatment.T2:
                return TopPop(recommendations_redis.connection, catalog.top_tracks_sticky_artist[:100])
            elif treatment == Treatment.T3:
                return TopPop(recommendations_redis.connection, catalog.top_tracks_top_pop[:100])
            elif treatment == Treatment.T4:
                return TopPop(recommendations_redis.connection, catalog.top_tracks_collaborative[:100])
            elif treatment == Treatment.T5:
                return TopPop(recommendations_redis.connection, catalog.top_tracks_contextual[:100])
            else:
                return Random(tracks_redis.connection)
        #DONE Описать стратегию для экперимента по сравнению с моделью Contextual
        elif self.name == "CONTEXTUAL_COMPARISON":
            # T1 Contextual with TopPop and filter
            # C Contextual
            if treatment == Treatment.T1:
                return Contextual_with_toppop(tracks_redis.connection, 
                                              history_redis.connection,  
                                              catalog,
                                              history,
                                              recommender_tolerance=0.65,
                                              toppoplen=100,
                                              filter_strategy="AUTHOR_TRACK_HISTORY",
                                              artist_tolerance=1)
            else:
                return Contextual(tracks_redis.connection, catalog)
                # return Contextual_with_toppop(tracks_redis.connection, 
                #                 history_redis.connection,  
                #                 catalog,
                #                 history,
                #                 recommender_tolerance=0.65,
                #                 toppoplen=100,
                #                 filter_strategy="SIMPLE_HISTORY",
                #                 artist_tolerance=1)
                
        elif self.name == "MANY_CONTEXTUAL_COMPARISON":
            # T1 Contextual with TopPop and filter SIMPLE 0.65
            # T2 Contextual with TopPop and filter SIMPLE 0.60
            # T3 Original Contextual
            # C Random
            if treatment == Treatment.T1:
                return Contextual_with_toppop(tracks_redis.connection, 
                                              history_redis.connection,  
                                              catalog,
                                              history,
                                              recommender_tolerance=0.65,
                                              toppoplen=100,
                                              filter_strategy="SIMPLE_HISTORY",
                                              artist_tolerance=3)
            elif treatment == Treatment.T2:
                return Contextual_with_toppop(tracks_redis.connection, 
                                              history_redis.connection,  
                                              catalog,
                                              history,
                                              recommender_tolerance=0.60,
                                              toppoplen=100,
                                              filter_strategy="SIMPLE_HISTORY",
                                              artist_tolerance=3)
            elif treatment == Treatment.T3:
                return Contextual(tracks_redis.connection, catalog)
            else:
                return Random(tracks_redis.connection)


class LastTrack(Resource):
    def post(self, user: int):
        start = time.time()
        args = parser.parse_args()
        history.clear(history_redis.connection, user)
        data_logger.log(
            "last",
            Datum(
                int(datetime.now().timestamp() * 1000),
                user,
                args.track,
                args.time,
                time.time() - start,
            ),
        )
        return {"user": user}


api.add_resource(Hello, "/")
api.add_resource(Track, "/track/<int:track>")
api.add_resource(NextTrack, "/next/<int:user>")
api.add_resource(LastTrack, "/last/<int:user>")


if __name__ == "__main__":
    app.run(host="0.0.0.0")
