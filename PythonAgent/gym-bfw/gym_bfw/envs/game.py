import gym.spaces
import numpy as np

from gym.spaces import Box
from collections import namedtuple

class Map:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.border = 0
        self.time = ''
        self.villages_count = 0
        self.villages = []
        self.units = []
        self.terrain = []

    def parse_json(self, json):
        self.width = json['width']
        self.height = json['height']
        self.border = json['border']
        self.time = json['time']
        self.villages_count = json['villages_count']
        self.villages = json['villages']
        self.units = json['units']
        self.terrain = json['terrain']


class Turn:
    def __init__(self):
        self.current = 0
        self.limit = 0

    def parse_json(self, json):
        self.current = json['current']
        self.limit = json['limit']

class Player:
    def __init__(self):
        self.side = 0
        self.gold = 0
        self.villages_count = 0
        self.units_count = 0

    def parse_json(self, json):
        self.side = json['side']
        self.gold = json['gold']
        self.villages_count = json['villages_count']
        self.units_count = json['units_count']


class Game():
    def __init__(self):
        self.map = Map()
        self.turn = Turn()
        self.ai = Player()
        self.finished = 0
        self.turn_limit = 0
        self.unit_types = []

    def get_observation(self):
        obs = np.zeros((self.map.width, self.map.height, 8))

        #terrain info
        for i in range(0, self.map.height):
            for j in range(0, self.map.width):
                obs[i][j][0] = self.parse_terrain(self.map.terrain[i][j])

                obs[i][j][1] = self.parse_building(self.map.terrain[i][j])

        #village owner
        for village in self.map.villages:
            if(village['owner'] not in (self.ai.side, 0)):
                obs[village['x']-1][village['y']-1][2] = -1
            else:
                obs[village['x']-1][village['y']-1][2] = village['owner']

        obs[:, :, 3:8] = self.get_units_map()

        return obs

    def parse_terrain(self, item):
        terrain_codes = ['A', 'B', 'D', 'E', 'F', 'G', 'H', 'I', 'M', 'Q', 'R', 'S', 'T', 'U', 'W', 'X']
        building_codes = [ 'K', 'V', 'C']
        total_codes = len(terrain_codes) + len(building_codes)

        for i, t in enumerate(terrain_codes):
            if item.find(t) != -1:
                return (i+1) / (total_codes)

        for i, t in enumerate(building_codes):
            if item.find(t) != -1:
                return (len(terrain_codes) + i+1) / (total_codes)

        return 0

    def parse_building(self, item):
        building_codes = [ 'K', 'V', 'C']
        for i, t in enumerate(building_codes):
            if item.find(t) != -1:
                return (i+1) / len(building_codes)
        return 0

    def get_units_map(self):
        units = np.zeros((self.map.width, self.map.height, 5))

        for unit in self.map.units:
            if unit['owner'] == self.ai.side:
                units[unit['x']-1][unit['y']-1][0] = 1
            else:
                units[unit['x']-1][unit['y']-1][0] = - 1

            if unit['canrecruit']:
                units[unit['x']-1][unit['y']-1][1] = 1
            else:
                units[unit['x']-1][unit['y']-1][1] = 0

            units[unit['x']-1][unit['y']-1][2] = self.get_unit_type(unit['type']) + 1
            units[unit['x']-1][unit['y']-1][3] = unit['hitpoints']/100
            units[unit['x']-1][unit['y']-1][4] = unit['moves']/10 #considering 10 as max movement

        return units

    def get_unit_type(self, type):
        return self.unit_types.index(type) / len(self.unit_types)


    def parse_json(self, json):
        self.map.parse_json(json['map'])
        self.turn.parse_json(json['turn'])
        self.ai.parse_json(json['own'])
        self.finished = json['game']['finished']
        self.turn_limit = json['game']['limit']
        self.unit_types = json['game']['unit_types']

    def get_villages_count(self, owner):
        return len([v for v in self.map.villages if v['owner'] == owner])

    def get_units_count(self, owner):
        return len([v for v in self.map.units if v['owner'] == owner])
