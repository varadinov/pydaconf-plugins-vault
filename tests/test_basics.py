import os
import pytest
import hvac
from pydaconf_plugins_vault.utils import parse_config_string
from pydaconf_plugins_vault.vault import VaultKvPlugin
import time
import requests

from testcontainers.core.container import DockerContainer


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
        policy_name = "read-userpass-policy"
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
            "root_token": root_token
        }



def test_parse_config_string() -> None:
    config_string  = "server=http://127.0.0.1:8200,auth_method=userpass,path=application/,key=username"
    config_value = parse_config_string(config_string)
    assert config_value['server'] == "http://127.0.0.1:8200"
    assert config_value['auth_method'] == 'userpass'
    assert config_value['path'] == "application/"
    assert config_value['key'] == "username"

def test_parse_config_string_case_insensitive() -> None:
    config_string  = "Server=http://127.0.0.1:8200,AUTH_METHOD=userpass,Path=application/,KEY=username"
    config_value = parse_config_string(config_string)
    assert config_value['server'] == "http://127.0.0.1:8200"
    assert config_value['auth_method'] == 'userpass'
    assert config_value['path'] == "application/"
    assert config_value['key'] == "username"


def test_plugin_read_kv_v2(openbao_container: dict) -> None:
    plugin = VaultKvPlugin()

    def callback(value: str) -> None:
        _ = value

    config_string  = f"server={openbao_container['url']},auth_method=userpass,path=application/,key=password,kv_version=2,mount_point=kv_v2"
    os.environ['VAULT_USERNAME'] = 'test'
    os.environ['VAULT_PASSWORD'] = 'test'
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
