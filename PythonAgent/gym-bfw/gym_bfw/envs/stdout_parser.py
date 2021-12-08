import re
import numpy as np
import logging
import json
from .game import Game
from .action_space import ActionSpace
from .game_ended_exception import GameEndedException
from .game_closed_exception import GameCloseException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_python_input_file_name(proc):
    return get_tag_value_from_std_out(proc, 'input-file')

def get_game_config(proc):
    return json.loads(get_tag_value_from_std_out(proc, 'game-config'))

def get_game_state(proc):
    game_state_json = get_game_state_json(proc)
    g =  Game()
    g.parse_json(game_state_json)
    return g

def get_game_state_json(proc):
    raw_json =  get_tag_value_from_std_out(proc, 'game-state')
    return json.loads(raw_json)

def get_action_space(proc):
    units_json = get_units_to_move_json(proc)

    act_spc =  ActionSpace()
    act_spc.parse_json(units_json)
    return act_spc

def get_units_to_move_json(proc):
    raw_json =  get_tag_value_from_std_out(proc, 'units-to-move')
    return json.loads(raw_json)

# based on https://github.com/DStelter94/ARLinBfW
def get_tag_value_from_std_out(proc, tag):
    tag_value = None
    while tag_value == None:

        return_code = proc.poll()
        if return_code is not None:
            logger.info("game fisnished with " + str(return_code))
            raise GameCloseException('')

        for line in iter(proc.stdout.readline, b''):
            line = line.decode('utf-8').rstrip()
            if (line.startswith('['+tag+']')):
                m = re.match(r'\['+tag+'](.*)', line)
                tag_value = m.group(1)
                return tag_value
            elif (line.startswith('[game-result]')):
                m = re.match(r'\[game-result](.*)', line)
                game_result = json.loads(m.group(1))
                raise GameEndedException(game_result['result'], game_result['playing_side'])
            elif (line.startswith('[debug]')):
                m = re.match(r'\[debug](.*)', line)
                logger.info(m.group(1))