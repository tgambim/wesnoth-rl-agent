import gym
import numpy as np
from functools import reduce

class Action:
    def __init__(self, unit, action):
        self.unit = unit
        self.action = action

class ActionSpace(gym.Space):
    def __init__(self):
        self.actions = []
        super(ActionSpace, self).__init__((None, 7))

    def parse_json(self, json):
        # move actions
        self.actions = [self._get_action(unit, action) for unit in json for action in unit["possible_moves"]]

    def _get_action(self, unit, action):
        if action['type'] == 'attack':
            target_x = action['target_x']-1
            target_y = action['target_y']-1
            target_new_hp = action['target_new_hp']
        else:
            target_x = 0
            target_y = 0
            target_new_hp = 0
        return unit['x'] - 1, unit['y'] - 1, action['x'] - 1, action['y'] - 1, ActionSpace.get_action_index_by_type(action['type']), target_x, target_y, target_new_hp #ActionSpace.get_target(action)

    def sample(self):
        n = self.np_random.randint(len(self.actions))
        return self.actions[n]

    @staticmethod
    def get_action_index_by_type(type):
        action_types = ['move', 'attack', 'recruit']
        return action_types.index(type)

    @staticmethod
    def get_action_type_by_index(index):
        action_types = ['move', 'attack', 'recruit']
        return action_types[index]

    @staticmethod
    def get_target(action):
        if action['type'] == 'attack':
            x_displacement = action['target_x'] - action['x'] + 1
            y_displacement = action['target_y'] - action['y'] + 1

            return y_displacement * 3 + x_displacement
        else:
            return 0

    @staticmethod
    def parse_action(action_tuple):
        action = {
            "x" : action_tuple[0]+1,
            "y" : action_tuple[1]+1,
            "action_x" : action_tuple[2]+1,
            "action_y" : action_tuple[3]+1,
            "type" : ActionSpace.get_action_type_by_index(action_tuple[4]),
        }
        if(action['type'] == 'attack'):
            action['target_x'] = action_tuple[5] +1
            action['target_y'] = action_tuple[6] +1

        return action

    @staticmethod
    def get_action_index(params):
        action_vars_max = (10, 10, 10, 10, 3, 9)

        return reduce(lambda x, v: x + v[1] * ActionSpace.calc_obs_param_weight(action_vars_max, v[0]), enumerate(params), 0)

    @staticmethod
    def get_action_tuple(index):
        action_vars_max = (10, 10, 10, 10, 3, 9)
        arr = [0 for a in range(len(action_vars_max))]

        val = index
        for k, _ in enumerate(arr):
            j = len(action_vars_max) - k - 1
            if j == 0:
                arr[j] = val
            else:
                w = ActionSpace.calc_obs_param_weight(action_vars_max, j)
                arr[j] = int(val / w)
                val = val % ActionSpace.calc_obs_param_weight(action_vars_max, j)
        return arr

    @staticmethod
    def calc_obs_param_weight(action_vars_max, n):
        return reduce(lambda x, value: x * value, list(action_vars_max)[0:n], 1)