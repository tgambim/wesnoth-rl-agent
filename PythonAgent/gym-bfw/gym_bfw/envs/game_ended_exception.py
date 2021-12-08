class GameEndedException(Exception):
    def __init__(self, result, playing_side):
        self.result = result
        self.playing_side = playing_side