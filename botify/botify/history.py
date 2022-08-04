import pickle
from typing import List

class History:
    """
    A helper class used to save history for user per session
    and store the data to redis.
    """

    def __init__(self, app):
        self.app = app

    def append_item(self, redis, user:int, new_item:int):
        self.app.logger.info(f"Append item {new_item} to user {user} history")
        user_history = redis.get(user)
        
        if user_history is None:
            history_list = [new_item]
        else:
            history_list = self.from_bytes(user_history)
            history_list.append(new_item)
            
        redis.set(user, self.to_bytes(history_list))
    
    def get(self, redis, user:int) -> List[int]:
        user_history = redis.get(user)
        if user_history is None:
            return []
        else:
            return self.from_bytes(user_history)
            
    def clear(self, redis, user:int):
        self.app.logger.info(f"Clear user {user} history")
        redis.set(user, self.to_bytes([]))
        
    def to_bytes(self, instance):
        return pickle.dumps(instance)

    def from_bytes(self, bts):
        return pickle.loads(bts)