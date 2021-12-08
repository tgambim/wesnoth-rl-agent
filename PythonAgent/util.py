import numpy as np


def get_action_matrix(map_width, map_height, action_tuple):
    action_matrix = np.zeros((map_width, map_height, 3))
    try:
        action_matrix[int(action_tuple[0]), int(action_tuple[1]), 0] = 1  # unit current coordinates
        action_matrix[int(action_tuple[2]), int(action_tuple[3]), 1] += (action_tuple[4]+1) / 3  # destiny coordinates
        if action_tuple[4] == 1:
            action_matrix[int(action_tuple[5]), int(action_tuple[
                6]), 2] = action_tuple[7]/100  # target coordinates in case of attack;
        return action_matrix
    except IndexError as e:
        print(action_tuple)
        print(action_matrix)
        print(e)
        raise e


def get_unit_next_moves(last_action, possible_actions):
    unit_new_possible_actions = [act for act in possible_actions
                                 if act[0] == last_action[2] and act[1] == last_action[3]]
    return unit_new_possible_actions


def unit_is_leader(act, obs):
    return obs[act[0]][act[1]][4] == 1
