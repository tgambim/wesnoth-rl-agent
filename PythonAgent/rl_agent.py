from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense, InputLayer, Conv2D, Flatten
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.losses import Huber
from tensorflow.keras.models import load_model
import tensorflow as tf
from collections import deque
import numpy as np
from util import get_action_matrix
from random import sample


class RLAgent:
    def __init__(self, obs_space_shape, action_space_n, load_model_from_file=False, model_file = 'trained_models/t11_non_linear_model_8'):
        self.alpha = 0.01
        self.gamma = 0.99
        self.epsilon = 1
        self.train_buffer_max_len = 50000

        self._observation_space_shape = obs_space_shape
        self._action_space_n = 1

        self.replay_buffer = deque(maxlen=self.train_buffer_max_len)

        if load_model_from_file:
            self.load_model(model_file)
        else:
            self.model = self._build_net()

        self.model.summary()

        self.target_model = self._build_net()
        self.update_target_model()

    def _build_net(self):
        input_shape = (
            self._observation_space_shape[0], self._observation_space_shape[1], self._observation_space_shape[2] + 3)

        model = Sequential([
            InputLayer(input_shape=input_shape),
            Conv2D(32, kernel_size=4, strides=2, activation='relu', data_format='channels_last'),
            Conv2D(64, kernel_size=2, strides=1, activation='relu', data_format='channels_last', ),
            Conv2D(64, kernel_size=2, strides=1, activation='relu', data_format='channels_last', ),
            Flatten(),
            Dense(512, activation='relu'),
            Dense(1, activation='linear')
        ])

        model.compile(loss=Huber(), optimizer=Adam(learning_rate=self.alpha, clipnorm=1.0))

        return model

    def update_target_model(self):
        self.target_model.set_weights(self.model.get_weights())

    def get_action(self, state, action_space, override_epsilon=1):
        if np.random.uniform(0, 1) < min(self.epsilon, override_epsilon):
            recruit_actions = [act for act in action_space.actions if act[4] == 2]
            attack_actions = [act for act in action_space.actions if act[4] == 1]
            move_actions = [act for act in action_space.actions if act[4] == 0]
            # TODO improve later
            action = None
            while action is None:
                rd = np.random.uniform(0, 3)
                if rd > 2:
                    if len(recruit_actions) > 0:
                        action = recruit_actions[np.random.randint(len(recruit_actions))]
                elif rd > 1:
                    if len(attack_actions) > 0:
                        action = attack_actions[np.random.randint(len(attack_actions))]
                else:
                    if len(move_actions) > 0:
                        action = move_actions[np.random.randint(len(move_actions))]

            q_value = self.model.predict(self._get_input_batch(state, np.array([action])))[0]
            return action, q_value, 1
        else:
            q_values = self.model.predict(self._get_input_batch(state, action_space.actions))

            argmax = np.argmax(q_values)
            return action_space.actions[argmax], q_values[argmax], 0

    # based on https://keras.io/examples/rl/deep_q_network_breakout/
    def update_batch_values(self, batch):
        batch = np.array(batch, dtype=object)
        state_actions = np.array([tf.convert_to_tensor(self._get_input(*sa))for sa in batch[:, 0:2]])
        new_state_actions = np.array([self._get_input_batch(*nsa) for nsa in batch[:, 2:4]], dtype=object)
        rewards = np.array(batch[:, 4], dtype='float32')
        dones = np.array([int(d) for d in batch[:, 5]], dtype='float32')

        future_state_values = {}
        future_state_actions = np.array([a for state_action in new_state_actions
                                         for a in state_action], dtype='float32')
        if len(future_state_actions) > 0:
            future_state_action_indexes = [i for i, state_action in enumerate(new_state_actions)
                                           for _ in state_action]
            future_state_actions_values = self.target_model.predict(future_state_actions)
            for i, index in enumerate(future_state_action_indexes):
                if index not in future_state_values.keys():
                    future_state_values[index] = []
                future_state_values[index].append(future_state_actions_values[i])

        future_rewards = [np.amax(np.array(future_state_values[i])) if i in future_state_values.keys() else 0
                               for i, state_action in enumerate(new_state_actions)]

        # multiply future rewards with 1-dones to ignore future rewards on terminal states
        future_rewards = np.multiply(future_rewards, (1-dones))
        # rw + disc * future_rw
        new_q_values = rewards + self.gamma * future_rewards
        new_q_values = np.array([[q] for q in new_q_values])
        self.model.fit(state_actions, new_q_values)

    def train(self, batch_size):
        if batch_size > len(self.replay_buffer):
            return False

        win_sample = []
        wins = [buffer for buffer in self.replay_buffer if buffer[4] == 1]
        if len(wins) > 0:
            win_sample = sample(wins, 1)

        batch = sample(self.replay_buffer, batch_size - len(win_sample)) + win_sample

        self.update_batch_values(batch)

    def save_replay_step(self, state, action, new_state, new_state_actions, reward, is_final_state):
        self.replay_buffer.append((state, action, new_state, new_state_actions, reward, is_final_state))

    def _get_input(self, state, action):
        act_matrix = get_action_matrix(self._observation_space_shape[0], self._observation_space_shape[1], action)

        return np.concatenate((state, act_matrix), axis=2)

    def _get_input_batch(self, state, actions):
        acts_matrix = [get_action_matrix(self._observation_space_shape[0], self._observation_space_shape[1], action) for
                       action in actions]

        return np.array([np.concatenate((state, act_matrix), axis=2) for act_matrix in acts_matrix])

    def load_model(self, file):
        self.model = load_model(file)

    def save_model(self, file):
        self.model.save(file)

