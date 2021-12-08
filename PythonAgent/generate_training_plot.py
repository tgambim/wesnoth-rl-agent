import numpy as np
import matplotlib.pyplot as plt
from plot_util import chunk_results

# train_variations = ["t12_", "t14_", "t16_", "t18_", "t19_"]
train_variations = ["t1_", "t2_", "t3_", "t4_", "t5_"]
# results_file = "training_results/training_non_linear_8/"
results_file = "test_results/linear_v2_t5/"

# episodes = 20000
episodes = 500

rewards = np.zeros(int(episodes/100))
eps = np.zeros(int(episodes/100))

wins = np.zeros(int(episodes/100))


for t in train_variations:
    rewards_file = results_file + t + 'rewards.npy'
    epsilon_file = results_file + t + 'epsilon.npy'

    variation_rewards = np.array([sum(rc)/100 for rc in chunk_results(np.load(rewards_file), 100)])
    # variation_eps = np.array([sum(rc)/100 for rc in chunk_results(np.load(epsilon_file), 100)])

    rewards = np.add(rewards, variation_rewards)
    # eps = np.add(eps, variation_eps)

    variation_wins = open(results_file + t + "results.txt", "r").readlines()
    variation_wins = [int(w.split(sep=";")[1].split(sep=" ")[2]) for w in variation_wins]
    for i in range(len(variation_wins)-1, 0, -1):
        variation_wins[i] -= variation_wins[i-1]
    wins = np.add(wins, np.array(variation_wins)/100)


rewards /= len(train_variations)
eps /= len(train_variations)
wins /= len(train_variations)

plt.clf()
x = list(range(100, episodes+1, 100))
plt.plot(x, rewards, label='Recompensa')
# plt.plot(x, eps, label='Epsilon')
plt.plot(x, wins, label='Taxa de Vitórias')
plt.xlabel('Episódios')
plt.ylabel('Resultados médios a cada 100 episódios')
# plt.ylim([-1, 1])
plt.ylim([-0.8, 0.2])
plt.legend()

try:
    plt.savefig(results_file + 'results_plot_mean.png')
except OSError:
    print('error saving training plot')


