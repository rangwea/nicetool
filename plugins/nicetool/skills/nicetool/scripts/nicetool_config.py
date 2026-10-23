import os
import tomllib

DEFAULT_SERVER = "http://localhost:8000"


class ConfigError(Exception):
    pass


def default_config_path(environ=None):
    if environ is None:
        environ = os.environ
    config_home = environ.get("XDG_CONFIG_HOME")
    if config_home:
        return os.path.join(os.path.expanduser(config_home), "nicetool", "config.toml")
    return os.path.join(os.path.expanduser("~"), ".config", "nicetool", "config.toml")


def resolve_config_path(explicit=None, environ=None):
    if environ is None:
        environ = os.environ
    configured = explicit or environ.get("NICETOOL_CONFIG")
    if configured:
        return os.path.abspath(os.path.expanduser(configured)), True
    return default_config_path(environ), False


def load_config(explicit=None, environ=None):
    path, required = resolve_config_path(explicit, environ)
    if not os.path.isfile(path):
        if required:
            raise ConfigError(f"配置文件不存在: {path}")
        return {}, path
    try:
        with open(path, "rb") as config_file:
            return tomllib.load(config_file), path
    except Exception as error:  # noqa: BLE001 — 保留边界兜底及现有错误响应，避免异常穿透改变调用契约。
        raise ConfigError(f"配置文件解析失败 {path}: {error}")


def load_credentials(environ=None):
    if environ is None:
        environ = os.environ
    path = environ.get("NICETOOL_CREDENTIALS")
    if not path:
        config_home = environ.get("XDG_CONFIG_HOME") or os.path.join("~", ".config")
        path = os.path.join(config_home, "nicetool", "credentials.env")
    path = os.path.abspath(os.path.expanduser(path))
    values = {}
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as source:
            for line in source:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def resolve_runtime(
    explicit_environment=None,
    explicit_config=None,
    explicit_server=None,
    explicit_token=None,
    environ=None,
):
    if environ is None:
        environ = os.environ
    config, config_path = load_config(explicit_config, environ)
    requested_environment = explicit_environment or environ.get("NICETOOL_ENV")
    environment = requested_environment
    if not environment and not explicit_server:
        environment = config.get("default_environment")
    profile = None
    if environment:
        environments = config.get("environments") or {}
        profile = environments.get(environment)
        if not isinstance(profile, dict):
            raise ConfigError(f"环境不存在: {environment}")

    profile_url = profile.get("url") if profile else None
    if profile is not None and not profile_url:
        raise ConfigError(f"环境 {environment} 未配置 url")
    server = (
        explicit_server or profile_url or environ.get("NICETOOL_URL") or DEFAULT_SERVER
    ).rstrip("/")

    token = explicit_token
    token_env = profile.get("token_env") if profile else None
    if token is None and token_env:
        token = environ.get(token_env) or load_credentials(environ).get(token_env)
        if not token:
            raise ConfigError(f"环境 {environment} 的 Token 未设置: {token_env}")
    if token is None:
        token = environ.get("NICETOOL_TOKEN", "")

    return {
        "config_path": config_path,
        "environment": "custom" if explicit_server else environment,
        "selected_environment": environment,
        "production": bool(profile and profile.get("production", False)),
        "server": server,
        "token": token,
    }
