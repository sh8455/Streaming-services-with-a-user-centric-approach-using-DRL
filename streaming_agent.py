import numpy as np
import gym
from gym import spaces
import video_streaming_comparison
from stable_baselines3 import DQN, A2C, PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnRewardThreshold
from stable_baselines3.common.results_plotter import load_results, plot_results
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

class CustomEnv(gym.Env):
    def __init__(self):
        super(CustomEnv, self).__init__()
        max_chunk_num = 20
        num_users = 3
        self.action_space = spaces.MultiDiscrete([10, 10, 6, 10, 10, 6, 10, 10, 6])
        self.observation_space = spaces.Box(low=0.1, high=100000, shape=(12,), dtype=np.float32)
        self.env = video_streaming_comparison.VideoStreaming(max_chunk_num=max_chunk_num, num_users=num_users)
    def step(self, action):
        observation, reward, done, info = self.env.step(action)
        return np.array(observation, dtype=np.float32), reward, done, info
    def reset(self):
        observation = self.env.reset()
        return np.array(observation, dtype=np.float32)
    def close (self):
        print("close")

# Main 함수
if __name__ == '__main__':
    env = CustomEnv()
    env = Monitor(env)
    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log="./logs/")
    eval_callback = EvalCallback(env, eval_freq=100, deterministic=True, render=False)
    model.learn(total_timesteps=100000, callback=[eval_callback])
    model.save("comparison_ppo_v1")
    results = load_results("logs/")
    plot_results(results, title="My Training Results")