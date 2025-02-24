# Pydaconf Plugin for Hashicorp Vault and OpenBao
Currently, the plugin supports only the KV (v1 and v2) secrets engines. The supported authentication methods are userpass, approle and token.
>**Note** If you need additional engines or authentication methods, please open a Feature Request [ISSUE](https://github.com/varadinov/pydaconf-plugins-vault/issues)

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/varadinov/pydaconf-plugins-vault/ci.yaml)
![GitHub last commit](https://img.shields.io/github/last-commit/varadinov/pydaconf-plugins-vault)
![GitHub](https://img.shields.io/github/license/varadinov/pydaconf-plugins-vault)
[![downloads](https://static.pepy.tech/badge/pydaconf-plugins-vault/month)](https://pepy.tech/project/pydaconf-plugins-vault)
![PyPI - Version](https://img.shields.io/pypi/v/pydaconf-plugins-vault)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pydaconf-plugins-vault)

## Pydaconf 
For more information about Pydaconf see the [Docs](https://varadinov.github.io/pydaconf/).

## Installation
Install using `pip install pydaconf-plugins-vault`  

## A Simple Example
* Create config file in toml, yaml or json
```yaml
secret: VAULT:///server=https://myvault.mydomain.com,auth_method=userpass,path=application/,key=password,kv_version=2,mount_point=kv_v2
```

* Create Pydantic Model and load the configuration
```python
from pydaconf import PydaConf
from pydantic import BaseModel


class Config(BaseModel):
    secret: str

provider = PydaConf[Config]()
provider.from_file("config.yaml")
print(provider.config.secret)
```
* Provide environment variables and run the app
```bash
export VAULT_USERNAME=myusername
export VAULT_PASSWORD=mypassword
python main.py
```

## Supported parameters
Parameters can be passed in the configuration value in the following format:
```
VAULT:///param1=value1,param2=value2
```

| Parameter  | Description                                                                                         |
|------------|-----------------------------------------------------------------------------------------------------|
| server     | URL to the vault or openbao instance                                                                |
| auth_method | Currently the plugin supprot userpass, approle and token authentication                             |
| path       | path to the secret in KV store                                                                      |
| key        | key of the secret that contains the specific credential                                             |
| kv_version | Supports version 1 or 2 of the KV secrets engine. If not provided, it will use version 2 by default |
| mount_point | Mount point of the KV secrets engine (e.g. kv/)                                                     |

## Authentication environment variables
Based on the provided authentication method, the plugin will use the following environment variables:
* userpass - VAULT_USERNAME and VAULT_PASSWORD
* approle - VAULT_APPROLE_ID and VAULT_APPROLE_SECRET
* token - VAULT_TOKEN

>**Note** You will need to provide the required variables before you start the application. 
