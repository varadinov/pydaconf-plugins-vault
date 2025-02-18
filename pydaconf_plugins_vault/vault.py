import os

import hvac
from collections.abc import Callable
from pydaconf.plugins.base import PluginBase
from pydaconf.utils.exceptions import PluginException

from pydaconf_plugins_vault.utils import parse_config_string


class VaultKvPlugin(PluginBase):
    """Pydaconf Plugins Vault plugin. Loads variables based on prefix VAULT:///"""

    PREFIX='VAULT'

    def __init__(self) -> None:
        self.client = hvac.Client()

    def run(self, value: str, on_update_callback: Callable[[str], None]) -> str:
        config_params = parse_config_string(value)
        self.client.url = config_params['server']
        key = config_params['key']
        if config_params['auth_method'].lower() == 'userpass':
            self.client.auth.userpass.login(
                username=os.environ['VAULT_USERNAME'],
                password=os.environ['VAULT_PASSWORD'],
            )

        kv_version = config_params.get('kv_version', "2")
        mount_point = config_params.get('mount_point', 'kv')
        if kv_version == "1":
            result = self.client.secrets.kv.v1.read_secret(
                path=config_params['path'],
                mount_point=mount_point,
            )
            return str(result['data'][key])

        elif kv_version == "2":
            result = self.client.secrets.kv.v2.read_secret_version(
                path=config_params['path'],
                mount_point=mount_point
            )
            return str(result['data']['data'][key])

        else:
            raise PluginException('Incorrect KV version. Supported versions are 1 and 2')


