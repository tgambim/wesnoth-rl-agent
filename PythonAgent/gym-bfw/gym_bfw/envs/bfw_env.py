import json

import gym
import re
import numpy as np
from gym import error, spaces, utils
from gym.utils import seeding
import subprocess
import sys
import os
from timeit import default_timer as timer
import logging
from . import stdout_parser, game
from .action_space import ActionSpace
from .game_ended_exception import GameEndedException
from .game_closed_exception import GameCloseException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('BfwEnv')

class BfwEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    wesnoth_process = None
    lua_ca_input_file = None
    game_config = {}

    last_gs = None

    action_id = 1

    def __init__(self):
        self.wesnoth_addons_folder = self.__get_wesnoth_addon_folder()
        #start wesnoth to load map config
        self.__launch_wesnoth()
        #kill wesnoth to restart on reset
        self.wesnoth_process.kill()
        self.wesnoth_process = None
        self.__delete_lua_ca_file()
        self.action_id = 1

    def __get_wesnoth_addon_folder(self):
        #logger.info('getting addon folder')
        process_args = ["wesnoth", "--userdata-path"]
        stdout = subprocess.check_output(process_args)

        #logger.info('addon folder: '+ stdout.decode(sys.stdout.encoding).strip())
        return stdout.decode(sys.stdout.encoding).strip()

    def __del__(self):
        if self.wesnoth_process is not None:
            if self.wesnoth_process.poll() is None:
                self.wesnoth_process.kill()

        self.__delete_lua_ca_file()

    def __delete_lua_ca_file(self):
        if self.lua_ca_input_file is not None and os.path.exists(self.lua_ca_input_file):
            os.remove(self.lua_ca_input_file)
            self.lua_ca_input_file = None

    def step(self, action):

        try:
            # check invalid actions
            if action not in self.action_space.actions:
                logger.info(f"invalid action {action}")
                return self.last_gs.get_observation(), -15, False, {}

            self.__send_action_to_lua(action)

            gs = stdout_parser.get_game_state(self.wesnoth_process)
            reward = self.__get_reward(self.last_gs, gs)
            is_new_turn = gs.turn.current != self.last_gs.turn.current
            self.last_gs = gs

            if self.wesnoth_process.poll() is not None:
                return gs, 0, True, {}

            self.action_space = stdout_parser.get_action_space(self.wesnoth_process)

            return gs.get_observation(), reward, gs.finished, {"is_new_turn":is_new_turn}

        except GameEndedException as g:
            if g.result== "victory":
                reward = 1
            else:
                reward = -1
            return self.last_gs.get_observation(), reward, True, {"is_new_turn":g.playing_side!=self.last_gs.ai.side}

    def __get_reward(self, old_gs, new_gs):
        reward = 0
        if new_gs.get_villages_count(1) > old_gs.get_villages_count(1): #new village reward
            reward += 0.05

        if new_gs.get_units_count(1) > old_gs.get_units_count(1): #recruit reward
            reward += 0.1 * (new_gs.get_units_count(1) - old_gs.get_units_count(1))

        if new_gs.get_units_count(2) < old_gs.get_units_count(2): # kill enemy reward
            reward += 0.05

        return reward


    def __send_action_to_lua(self, action):
        action = ActionSpace.parse_action(action)
        # send action as Lua Table
        if action["type"] == 'attack':
            data = [
                'target_x='+str(action['target_x']) + ',',
                'target_y='+str(action['target_y']) + ',',
                'weapon="best"'
            ]
            extra = '{'
            for d in data:
                extra+=d
            extra += '}'
        elif action["type"] == 'recruit':
            extra = '{recruit_type="best"}'
        else:
            extra= '{}'

        text = f'return {action["x"]}, {action["y"]}, "{action["type"]}", {action["action_x"]}, {action["action_y"]}, {extra}, {self.action_id}\n'
        self.__write_on_ca_file(text)
        self.action_id = int(not self.action_id)

    def reset(self):
        self.__launch_wesnoth()
        gs = stdout_parser.get_game_state(self.wesnoth_process)
        self.action_space = stdout_parser.get_action_space(self.wesnoth_process)
        self.last_gs = gs
        return self.last_gs.get_observation()

    # based on https://github.com/DStelter94/ARLinBfW
    def __launch_wesnoth(self):
        self.__delete_lua_ca_file()

        while True:
            try:
                if self.wesnoth_process is None or self.wesnoth_process.poll() is not None:
                    process_args = ["wesnoth", "--nodelay", "--nogui", "--nosound",
                                    "--multiplayer", "--exit-at-end", #"--log-info", "wml",
                                    "--multiplayer-repeat", str(1000000),
                                    "--scenario", "python_test"]

                    self.wesnoth_process = subprocess.Popen(process_args, stdout=subprocess.PIPE)

                self.__create_lua_ca_file()
                self.__load_game_config()

                if self.lua_ca_input_file is None:
                    self.wesnoth_process.kill()
                    self.wesnoth_process = None
                else:
                    break
            except GameCloseException as g:
                logger.info('game reset')

    def __write_on_ca_file(self, text):
        f = open(self.lua_ca_input_file, "w")
        f.write(text)
        f.close()

    def render(self, mode='human'):
        return ''

    def close(self):
        self.__kill_game()

    def __kill_game(self):
        if self.wesnoth_process is not None:
            self.wesnoth_process.kill()
            self.wesnoth_process = None
            self.__delete_lua_ca_file()

    # https://github.com/DStelter94/ARLinBfW
    def __create_lua_ca_file(self):
        input_path = stdout_parser.get_python_input_file_name(self.wesnoth_process)

        self.lua_ca_input_file = self.wesnoth_addons_folder + "/data" + input_path.replace("~", "")
        self.__write_on_ca_file("return '', -1, -1, '', -1, -1, -1")
        return self.lua_ca_input_file

    def __load_game_config(self):
        self.game_config = stdout_parser.get_game_config(self.wesnoth_process)
        self.action_space = spaces.Box(low=0.0, high=1.0, shape=(100, 7))
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(self.game_config['map_width'], self.game_config['map_height'], 8), dtype=np.float32)
