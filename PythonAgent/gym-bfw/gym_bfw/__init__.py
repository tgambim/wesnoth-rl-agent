from gym.envs.registration import register

register(
    id='bfw-v0',
    entry_point='gym_bfw.envs:BfwEnv',
)