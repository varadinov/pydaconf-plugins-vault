# Pydaconf Plugin for Hashicorp Vault and OpenBao

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
secret: VAULT:///secret_name=my-secret
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

## Supported parameters
Parameters can be passed in the configuration value in the following format:
```
VAULT:///param1=value1,param2=value2
```

| Parameter | Description                |
|-----------|----------------------------|
| param1    | The description of param 1 |
| param2    | The description of param 2 |