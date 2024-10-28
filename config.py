import os

from dotenv import dotenv_values
from pydantic import BaseModel




class Config(BaseModel):
    TELEGRAM_KEY: str


shared_env = dotenv_values(".env.shared")
env = dotenv_values(".env")
os_env = os.environ

combined_env = {**shared_env, **env, **os_env}

config = Config(**combined_env)