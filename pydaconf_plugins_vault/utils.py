import re

from pydaconf_plugins_vault.config_model import ConfigParams


def parse_config_model(config: str) -> ConfigParams:
    config_dict = parse_config_params(config)
    return ConfigParams(**config_dict)

def parse_config_params(config: str) -> dict:
    """Parses a key=value string into a dictionary using regex, handling optional fields."""

    pattern = re.compile(r'(\w+)=([^,]+)')
    result = {}

    for match in pattern.findall(config):
        key, value = match

        # Convert booleans to actual bool type
        if value.lower() in {'true', 'false'}:
            value = value.lower() == 'true'
        result[key.lower()] = value

    return result