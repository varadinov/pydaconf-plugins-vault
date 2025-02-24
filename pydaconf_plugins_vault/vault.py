import logging
import os
from collections.abc import Callable

import hvac
from pydaconf.plugins.base import PluginBase
from pydaconf.utils.exceptions import PluginException

from pydaconf_plugins_vault.utils import parse_config_model


class VaultKvPlugin(PluginBase):
    """Pydaconf Vault KV Plugins. Loads variables based on prefix VAULT:///"""

    PREFIX='VAULT'

    def __init__(self) -> None:
        self.client = hvac.Client()
        self.logger = logging.getLogger(__name__)

    def _login(self, method: str) -> None:
        if method == 'userpass':
            username = os.environ.get('VAULT_USERNAME')
            password = os.environ.get('VAULT_PASSWORD')

            if username is None or password is None:
                raise PluginException(
                    "VAULT_USERNAME and VAULT_PASSWORD environment variables are required to use 'userpass' auth method.")

            self.client.auth.userpass.login(
                username=username,
                password=password,
            )

        elif method == 'approle':
            approle_id = os.environ.get('VAULT_APPROLE_ID')
            approle_secret = os.environ.get('VAULT_APPROLE_SECRET')

            if approle_id is None or approle_secret is None:
                raise PluginException(
                    "VAULT_APPROLE_ID and VAULT_APPROLE_SECRET environment variables are required to use 'approle' auth method.")

            self.client.auth.approle.login(
                role_id= approle_id,
                secret_id = approle_secret
            )

        elif method == 'token':
            token = os.environ.get('VAULT_TOKEN')

            if token is None:
                raise PluginException(
                    "VAULT_TOKEN environment variable is required to use 'token' auth method.")

            self.client.token = os.environ['VAULT_TOKEN']

    def run(self, value: str, on_update_callback: Callable[[str], None]) -> str:
        config_params = parse_config_model(value)
        self.client.url = config_params.server

        self.logger.debug(f"Login to vault using authentication method '{config_params.auth_method}'")
        self._login(config_params.auth_method)

        if config_params.kv_version == 1:
            self.logger.debug(f"Use kv1 secrets engine to retrieve secret '{value}'")
            result = self.client.secrets.kv.v1.read_secret(
                path=config_params.path,
                mount_point=config_params.mount_point,
            )
            if config_params.key not in result['data']:
                raise PluginException(
                    f"The required secret key '{config_params.key}' is not found in path '{config_params.path}'. '{value}'")

            return str(result['data'][config_params.key])

        elif config_params.kv_version == 2:
            self.logger.debug(f"Use kv2 secrets engine to retrieve secret '{value}'")
            result = self.client.secrets.kv.v2.read_secret_version(
                path=config_params.path,
                mount_point=config_params.mount_point,
                raise_on_deleted_version=False,
            )
            if config_params.key not in result['data']['data']:
                raise PluginException(
                    f"The required secret key '{config_params.key}' is not found in path '{config_params.path}'. '{value}'")

            return str(result['data']['data'][config_params.key])

        else:
            raise PluginException("Incorrect KV version. The supported versions are 1 or 2")

