import sys

import gym
import numpy as np
from rl_agent import RLAgent
from plot_util import plot_rewards

test_variation = ""
if len(sys.argv) > 1:
    test_variation = sys.argv[1] + "_"

env = gym.make('gym_bfw:bfw-v0')

agent = RLAgent(env.observation_space.shape, env.action_space.shape, True, "trained_models/t14_non_linear_model_8")

# folder where results will be saved
results_file = "test_results/non_linear_8_t14/"
rewards_file = results_file + test_variation + 'rewards.npy'
epsilon_file = results_file + test_variation + 'epsilon.npy'

episodes = 501
epsilon = 0

wins = 0
loses = 0

rewards = np.zeros(episodes-1)
eps = np.zeros(episodes-1)

for current_episode in range(1, episodes):
    obs = env.reset()
    steps, reward = 0, 0
    done = False
    episode_reward = 0

    while not done:
        action, _, _ = agent.get_action(obs, env.action_space, epsilon)
        new_obs, reward, done, info = env.step(action)

        print(f"game {current_episode}; step {steps}; action type {action[4]}; reward {reward}")

        episode_reward += reward

        next_actions = env.action_space.actions

        if reward == -1:
            print(f"game {current_episode}: lose")
            loses += 1
        if reward == 1:
            print(f"game {current_episode}: win")
            wins += 1

        obs = new_obs
        steps += 1

    if current_episode % 100 == 0:
        f = open(results_file + test_variation + "results.txt", "a")
        f.write(f'games: {current_episode}; wins: {wins}; loses: {loses}\n')
        f.close()

    rewards[current_episode - 1] = episode_reward
    eps[current_episode - 1] = epsilon

plot_rewards(rewards, eps, results_file + test_variation + 'results_plot.png')

with open(rewards_file, 'wb') as f:
    np.save(f, rewards)
with open(epsilon_file, 'wb') as f:
    np.save(f, eps)

