import os
import time

import hvac
import pytest
import requests
from pydaconf.utils.exceptions import PluginException
from testcontainers.core.container import DockerContainer

from pydaconf_plugins_vault.utils import parse_config_params
from pydaconf_plugins_vault.vault import VaultKvPlugin


@pytest.fixture(scope="session")
def openbao_container() -> DockerContainer:
    """Pytest fixture to set up OpenBao in Testcontainers and configure it."""

    with DockerContainer("openbao/openbao:latest") as container:
        # Start OpenBao container
        container.with_exposed_ports(8200)
        container.start()

        # Get OpenBao connection details
        container_ip = container.get_container_host_ip()
        container_port = container.get_exposed_port(8200)
        url = f"http://{container_ip}:{container_port}"

        # Wait for OpenBao to become ready
        health_url = f"http://{container_ip}:{container_port}/v1/sys/health"
        for _ in range(30):  # Retry for 30 seconds
            try:
                response = requests.get(health_url)
                if response.status_code in [200, 429]:  # Ready status
                    break
            except requests.ConnectionError:
                pass
            time.sleep(1)

        # Get root token (method depends on OpenBao configuration)
        logs = container.get_logs()[0].decode()
        root_token = None
        for line in logs.splitlines():
            if "Root Token:" in line:
                root_token = line.split(":")[1].strip()
                break

        # Create an hvac client
        client = hvac.Client(url=url, token=root_token)

        # Enable userpass authentication
        client.sys.enable_auth_method("userpass")

        # Create a policy
        policy_name = "read-policy"
        policy_rules = """
        path "kv_v2/*" {
          capabilities = ["read", "list"]
        }
        path "kv_v1/*" {
          capabilities = ["read", "list"]
        }
        """
        client.sys.create_or_update_policy(name=policy_name, policy=policy_rules)

        # Create a user with the policy
        username = "test"
        password = "test"
        client.auth.userpass.create_or_update_user(username=username, password=password, policies=[policy_name])

        # Create approle and assign policy
        auth_methods = client.sys.list_auth_methods()['data']
        if 'approle/' not in auth_methods:
            client.sys.enable_auth_method(method_type='approle', path='approle')

        role_name = 'test'
        client.auth.approle.create_or_update_approle(
            role_name=role_name,
            token_policies=['default', 'openbau-policy', 'read-policy'],
            token_ttl='1h',
            token_max_ttl='4h',
            secret_id_ttl='24h'
        )
        role_id = client.auth.approle.read_role_id(role_name=role_name)['data']['role_id']
        secret_id = client.auth.approle.generate_secret_id(role_name=role_name)['data']['secret_id']

        # Create token and assign policy
        token_data = client.auth.token.create(policies=['read-policy'], ttl='1h')

        # Enable KV v1 secret engine
        client.sys.enable_secrets_engine(backend_type="kv", path="kv_v1", options={"version": 1})

        # Enable KV v2 secret engine
        client.sys.enable_secrets_engine(backend_type="kv", path="kv_v2", options={"version": 2})

        # Store a secret in kv_v1
        client.secrets.kv.v1.create_or_update_secret(path="application", secret={"password": "pass"}, mount_point="kv_v1")

        # Store a secret in kv_v2
        client.secrets.kv.v2.create_or_update_secret(path="application", secret={"password": "pass"}, mount_point="kv_v2")

        # Provide the initialized OpenBao client
        yield {
            "url": url,
            "root_token": root_token,
            'role_id': role_id,
            'secret_id': secret_id,
            'token': token_data['auth']['client_token'],
            'username': username,
            'password': password
        }



def test_parse_config_string() -> None:
    config_string  = "server=http://127.0.0.1:8200,auth_method=userpass,path=application/,key=username"
    config_value = parse_config_params(config_string)
    assert config_value['server'] == "http://127.0.0.1:8200"
    assert config_value['auth_method'] == 'userpass'
    assert config_value['path'] == "application/"
    assert config_value['key'] == "username"

def test_parse_config_string_case_insensitive() -> None:
    config_string  = "Server=http://127.0.0.1:8200,AUTH_METHOD=userpass,Path=application/,KEY=username"
    config_value = parse_config_params(config_string)
    assert config_value['server'] == "http://127.0.0.1:8200"
    assert config_value['auth_method'] == 'userpass'
    assert config_value['path'] == "application/"
    assert config_value['key'] == "username"


def test_plugin_read_userpass_kv_v2(openbao_container: dict) -> None:
    plugin = VaultKvPlugin()

    def callback(value: str) -> None:
        _ = value

    config_string  = f"server={openbao_container['url']},auth_method=userpass,path=application/,key=password,kv_version=2,mount_point=kv_v2"
    os.environ['VAULT_USERNAME'] = openbao_container['username']
    os.environ['VAULT_PASSWORD'] = openbao_container['password']
    secret_value = plugin.run(config_string, callback)
    assert secret_value == 'pass'

def test_plugin_read_userpass_missing_key_kv_v2(openbao_container: dict) -> None:
    plugin = VaultKvPlugin()

    def callback(value: str) -> None:
        _ = value

    config_string  = f"server={openbao_container['url']},auth_method=userpass,path=application/,key=username,kv_version=2,mount_point=kv_v2"
    os.environ['VAULT_USERNAME'] = openbao_container['username']
    os.environ['VAULT_PASSWORD'] = openbao_container['password']
    with pytest.raises(expected_exception=PluginException, match=f"The required secret key 'username' is not found in path 'application/'. '{config_string}'"):
        _ = plugin.run(config_string, callback)

def test_plugin_read_userpass_missing_key_kv_v1(openbao_container: dict) -> None:
    plugin = VaultKvPlugin()

    def callback(value: str) -> None:
        _ = value

    config_string  = f"server={openbao_container['url']},auth_method=userpass,path=application/,key=username,kv_version=1,mount_point=kv_v1"
    os.environ['VAULT_USERNAME'] = openbao_container['username']
    os.environ['VAULT_PASSWORD'] = openbao_container['password']
    with pytest.raises(expected_exception=PluginException, match=f"The required secret key 'username' is not found in path 'application/'. '{config_string}'"):
        _ = plugin.run(config_string, callback)

def test_plugin_read_kv_approle_v2(openbao_container: dict) -> None:
    plugin = VaultKvPlugin()

    def callback(value: str) -> None:
        _ = value

    config_string  = f"server={openbao_container['url']},auth_method=approle,path=application/,key=password,kv_version=2,mount_point=kv_v2"
    os.environ['VAULT_APPROLE_ID'] = openbao_container['role_id']
    os.environ['VAULT_APPROLE_SECRET'] = openbao_container['secret_id']
    secret_value = plugin.run(config_string, callback)
    assert secret_value == 'pass'

def test_plugin_read_kv_token_v2(openbao_container: dict) -> None:
    plugin = VaultKvPlugin()

    def callback(value: str) -> None:
        _ = value

    config_string  = f"server={openbao_container['url']},auth_method=token,path=application/,key=password,kv_version=2,mount_point=kv_v2"
    os.environ['VAULT_TOKEN'] = openbao_container['token']
    secret_value = plugin.run(config_string, callback)
    assert secret_value == 'pass'


def test_plugin_read_kv_v1(openbao_container: dict) -> None:
    plugin = VaultKvPlugin()

    def callback(value: str) -> None:
        _ = value

    config_string  = f"server={openbao_container['url']},auth_method=userpass,path=application/,key=password,kv_version=1,mount_point=kv_v1"
    os.environ['VAULT_USERNAME'] = 'test'
    os.environ['VAULT_PASSWORD'] = 'test'
    secret_value = plugin.run(config_string, callback)
    assert secret_value == 'pass'
