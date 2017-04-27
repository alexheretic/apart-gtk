from datetime import timedelta
import os
from typing import *
import yaml
from apartcore import default_datetime_to_utc


def config_directory() -> str:
    env_dir = os.environ.get('APART_GTK_CONFIG_DIR')
    if env_dir and env_dir.endswith('/'):
        env_dir = env_dir[:-1]
    default_dir = os.path.expanduser('~') + '/.config/apart-gtk'
    return env_dir or default_dir


def history_path() -> str:
    return config_directory() + '/history.yaml'


def read_history() -> List[Dict]:
    if not os.path.exists(history_path()):
        return []
    with open(history_path(), 'r') as file:
        return default_datetime_to_utc(yaml.load(file.read()))


def write_history(history: List[Dict]):
    if not os.path.exists(history_path()):
        os.makedirs(os.path.dirname(history_path()))
    with open(history_path(), 'w') as file:
        file.write(yaml.dump(history))


def animation_duration_ms() -> int:
    return 200
