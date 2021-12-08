
import matplotlib.pyplot as plt


def plot_rewards(rewards, epsilon, file_name):
    plt.clf()
    plt.plot(rewards, label='Reward')
    plt.plot(epsilon, label='Epsilon')
    # plt.plot(predicted_rewards[:(current_episode - 1)], label='Predicted Reward')
    plt.xlabel('Episodes')
    plt.ylabel('Sum of rewards during episode')
    plt.ylim([-2, 3])
    plt.legend()

    try:
        plt.savefig(file_name)
    except OSError as e:
        print('error saving training plot')
        print(e)


def chunk_results(result_list, chunk_size):
    for i in range(0, len(result_list), chunk_size):
        yield result_list[i:i + chunk_size]
