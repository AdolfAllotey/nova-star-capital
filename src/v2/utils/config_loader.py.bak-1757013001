import json
import os

def load_config(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Config file not found: {file_path}")
    with open(file_path, 'r') as f:
        return json.load(f)

def load_email_config():
    config_path = "src/v2/config/email_config.json"
    return load_config(config_path)

def load_openai_config():
    config_path = "src/v2/config/openai_config.json"
    return load_config(config_path)

def load_api_keys():
    config_path = "src/v2/config/api_keys.json"
    return load_config(config_path)