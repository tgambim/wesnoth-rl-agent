import os
import random
import sys

import gym
from util import *
import numpy as np
import math
from rl_agent import RLAgent
from os import walk
import matplotlib.pyplot as plt
from util import get_unit_next_moves

env = gym.make('gym_bfw:bfw-v0')

agent = RLAgent(env.observation_space.shape, env.action_space.shape, False)

train_variation = ""
if len(sys.argv) > 1:
    train_variation = sys.argv[1]+"_"

results_file = "training_results/training_non_linear_9/"+train_variation
rewards_file = results_file + 'rewards.npy'
epsilon_file = results_file + 'epsilon.npy'


episodes = 20001
epsilon = 0.01

min_epsilon = 0.03
epsilon_const = np.log(min_epsilon)

wins = 0
loses = 0

eps = np.zeros(episodes-1)
rewards = np.zeros(episodes-1)

current_global_step = 1

train_after = 1
update_target_model_after = 500

train_batch_size = 32
train_buffer_max_len = agent.train_buffer_max_len

for current_episode in range(1, episodes):
    epsilon = math.exp(epsilon_const * current_episode/episodes)
    obs = env.reset()
    steps, reward = 0, 0
    done = False
    episode_reward = 0
    turn_data = []

    while not done:

        action, predicted_value, exploring = agent.get_action(obs, env.action_space, epsilon)

        new_obs, reward, done, info = env.step(action)

        print(f"game {current_episode}; step {steps}; action type {action[4]}; reward {reward}; predicted value {predicted_value}; exploring {exploring}")

        episode_reward += reward
        next_actions = env.action_space.actions

        if reward != -1 or not info['is_new_turn']:  # if lose in enemy turn, -1 reward need to go to leader unit
            unit_reward = reward
        else:
            unit_reward = 0
        turn_data.append([obs, action, new_obs, next_actions, unit_reward, done])

        if info['is_new_turn'] or done:
            for j in range(len(turn_data)):
                if reward == -1 and info['is_new_turn']:  # if lose in enemy turn, -1 reward need to go to leader unit
                    if unit_is_leader(turn_data[j][1], turn_data[j][0]):
                        turn_data[j][4] += reward

                # update unit next moves based on new turn available_actions and observation to new turn observation
                if (len(turn_data[j][3]) == 0) and not done:  # if the action wasn't recruit, set next turn actions
                    unit_new_possible_actions = get_unit_next_moves(turn_data[j][1], env.action_space.actions)
                    if len(unit_new_possible_actions) == 0:
                        turn_data[j][4] -= 0.02  # no action, unit died then add negative reward
                    turn_data[j][3] = unit_new_possible_actions
                    turn_data[j][2] = new_obs

            for d in turn_data:
                agent.save_replay_step(*d)
            turn_data.clear()

        if reward == -1:
            print(f"game {current_episode}: lose")
            loses += 1
        if reward == 1:
            print(f"game {current_episode}: win")
            wins += 1

        obs = new_obs
        steps += 1
        current_global_step += 1

    rewards[current_episode - 1] = episode_reward
    eps[current_episode - 1] = epsilon

    if current_episode % train_after == 0:
        train_steps = max(steps, int(math.ceil(steps * 2 * len(agent.replay_buffer)/agent.train_buffer_max_len)))
        for i in range(train_steps):
            agent.train(train_batch_size)

    if current_episode % update_target_model_after == 0:
        agent.update_target_model()

    if current_episode % 100 == 0:
        f = open(results_file + "results.txt", "a")
        f.write(f'games: {current_episode}; wins: {wins}; loses: {loses}\n')
        f.close()
        print(f"--------------------------- Episode: {current_episode} -----------------------------------")

        plt.clf()
        plt.plot(rewards[:(current_episode - 1)], label='Reward')
        plt.plot(eps[:(current_episode - 1)], label='Epsilon')
        # plt.plot(predicted_rewards[:(current_episode - 1)], label='Predicted Reward')
        plt.xlabel('Episodes')
        plt.ylabel('Sum of rewards during episode')
        plt.ylim([-2, 3])
        plt.legend()

        try:
            plt.savefig(results_file + 'results_plot.png')
        except OSError:
            print('error saving training plot')

    # every 1000 games, save model and results
    if current_episode % 1000 == 0:
        agent.save_model('trained_models/' + train_variation + 'non_linear_model_9')
        with open(rewards_file, 'wb') as f:
            np.save(f, rewards)
        with open(epsilon_file, 'wb') as f:
            np.save(f, eps)

print("Training finished.\n")
