import os
import json
import inspect
import hashlib
import functools
from uuid import UUID
from dataclasses import dataclass
from pathlib import Path
from fnmatch import fnmatch
from typing import Callable, Optional, Dict, Any, Union, List

try:
    import tomllib as toml
except ImportError:
    import tomli as toml

from oneupload.utils import get_app_dir, import_module
from oneupload.config import DEFAULT_CONFIG, INIT_CONFIG_TEXT

PACKAGE_NAME = 'oneupload'

HOME_ENV = 'ONEUPLOAD_HOME'

HOME_DEFAULT = get_app_dir(PACKAGE_NAME)

CONFIG_FILE = 'config.toml'
USER_CONFIG_FILE = 'user_config.toml'
DATA_FILE = 'data.json'


class ConfigError(Exception):
    pass


class NoAvailableUploaderError(Exception):
    pass


class UploaderNotFoundError(Exception):
    pass


class UploaderNotAvailableError(Exception):
    pass


class UploaderImportError(ImportError):
    pass


class UploadError(Exception):
    pass


@dataclass
class UploaderClient:
    name: str
    path: str

    args: Optional[Dict] = None
    requirements: Optional[List[str]] = None
    factory: Optional[Callable[..., Any]] = None

    def __post_init__(self):
        print(f'Initialize Client: {self.name}')
        self.factory = self._import_factory()

    def _import_factory(self) -> Optional[Callable[..., Any]]:
        try:
            mod, attr = import_module(self.path)
        except ImportError:
            return
        if attr and callable(attr):
            return attr

    def build(self, **kwargs):
        factory = self.factory
        assert callable(factory), f'{factory} is not callable!'
        return factory(**kwargs)

    def available(self):
        return self.factory is not None


@dataclass
class Uploader:
    name: str
    client: UploaderClient
    priority: int
    args: Optional[Dict[str, Any]] = None
    unique_id: Optional[str] = None
    instance: Optional[Any] = None
    upload_method: Optional[Callable[..., str]] = None

    def __post_init__(self):
        print(f'Initialize Uploader: {self.name}')
        if self.client.available():
            kwargs = {k.lower(): v for k, v in self.args.items()}
            self.instance = self.client.build(**kwargs)
            if inspect.isfunction(self.instance):
                self.upload_method = self.instance
            elif getattr(self.instance, 'upload', None):
                self.upload_method = getattr(self.instance, 'upload')
            elif callable(self.instance):
                self.upload_method = self.instance
            else:
                self.upload_method = None
            if not self.unique_id:
                default_unique_id = self.name
                self.unique_id = getattr(self.instance, 'unique_id', default_unique_id)
        else:
            print(f'Uploader cannot work because of client is unavailable: {self.name}')

    def upload(self, path, **kwargs) -> str:
        return self.upload_method(path, **kwargs)

    def available(self):
        return callable(self.upload_method)


@dataclass
class UploadRule:
    """上传规则"""
    name: str
    pattern: str
    uploader: str
    match_mode: str = 'name'
    plugins: List[str] = None

    def match(self, path: Path) -> bool:
        return fnmatch(path.name, self.pattern)


class UploaderProxy:
    """Upload files through uploader."""

    def __init__(self, config_path=None, home=None, **kwargs):
        home = home or os.getenv(HOME_ENV, HOME_DEFAULT)
        self._home = Path(home).expanduser()
        if not self._home.exists():
            self._home.mkdir(parents=True)
        if not self._home.is_dir():
            raise ValueError(f'"{home}" is not a directory.')

        self._app_config_path = self._home.joinpath(CONFIG_FILE)
        _force_init = kwargs.pop('force_init', False)
        if not self._app_config_path.is_file() or _force_init:
            self._app_config_path.write_text(INIT_CONFIG_TEXT, encoding='utf-8')

        if config_path:
            self.user_config_path = Path(config_path)
            if not self.user_config_path.is_file():
                raise ValueError(f'File not exists: {config_path}')
        else:
            self.user_config_path = self._home.joinpath(USER_CONFIG_FILE)

        # load config
        self.app_config, self.user_config = self._load_config()
        self._cfg_clients = self._get_config('client')
        self._cfg_uploaders = self._get_config('uploader')
        self._cfg_plugins = self._get_config('plugin')
        self._cfg_rules = self._get_config('rule')

        self._clients: Dict[str, UploaderClient] = self._init_clients()
        self._uploaders: Dict[str, Uploader] = self._init_uploaders()
        self._plugins: Dict = self._init_plugins()
        self._rules: Dict[str, UploadRule] = self._init_rules()

        self._selected_uploader = None

        self._data_path = self._home.joinpath(DATA_FILE)
        if self._data_path.is_file():
            self._history_data = json.loads(self._data_path.read_text(encoding='utf-8'))
        else:
            self._history_data = {}

    def _load_config(self):
        app_config = toml.loads(self._app_config_path.read_text(encoding='utf-8'))
        if not isinstance(app_config, dict):
            raise ValueError(f'"{self._app_config_path}" has invalid content.')

        if self.user_config_path and self.user_config_path.is_file():
            user_config = toml.loads(self.user_config_path.read_text(encoding='utf-8'))
            if not isinstance(user_config, dict):
                raise ValueError(f'"{self.user_config_path}" has invalid content.')
        else:
            user_config = {}
        return app_config, user_config

    def _get_config(self, name):
        _cfg = DEFAULT_CONFIG.get(name, {})
        _cfg.update(self.app_config.get(name, {}))
        _cfg.update(self.user_config.get(name, {}))
        return _cfg

    def _init_clients(self):
        _clients = {}
        for name in self._cfg_clients:
            client_cfg = self._cfg_clients[name].copy()
            uc = UploaderClient(name, **client_cfg)
            print(uc)
            if uc.name not in _clients:
                _clients[uc.name] = uc
            else:
                raise ValueError(f'Client name already exists: {uc.name}.')
        return _clients

    def _init_uploaders(self):
        _uploaders = {}
        for name in self._cfg_uploaders:
            uploader_cfg = self._cfg_uploaders[name].copy()
            client_name = uploader_cfg.pop('client', name)
            if client_name not in self._clients:
                raise ValueError(f"Invalid client: {client_name}")
            client = self._clients[client_name]
            if not client.available():
                print(f'Client {client_name} not available!')
                continue
            priority = uploader_cfg.pop('priority', 5)
            ue = Uploader(name, client=client, priority=priority, args=uploader_cfg)
            if not ue.available():
                print(f'Uploader {name} not available!')
            if ue.name not in _uploaders:
                _uploaders[ue.name] = ue
            else:
                raise ValueError(f'Uploader name already exists: {ue.name}.')
        return _uploaders

    def _init_plugins(self):
        _plugins = {}
        for name in self._cfg_plugins:
            plugin_pth = self._cfg_plugins[name]
            _, plugin = import_module(plugin_pth)
            _plugins[name] = plugin
        return _plugins

    def _init_rules(self):
        _rules = {}
        for name in self._cfg_rules:
            rule_cfg = self._cfg_rules[name]
            uploader_name = rule_cfg.pop('uploader')
            if uploader_name not in self._uploaders:
                raise ConfigError(f'uploader {uploader_name} not exists.')
            rule = UploadRule(name, uploader=uploader_name, **rule_cfg)
            _rules[name] = rule
        return _rules

    @property
    def current_uploader(self):
        if not self._selected_uploader:
            self._auto_select()
        return self._selected_uploader

    def __call__(self, path, **kwargs):
        return self.run_upload(path=path, **kwargs)

    def run_upload(self, path: Union[str, Path], **kwargs):
        if isinstance(path, str):
            path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f'{path} 不存在。')

        uploader_name = kwargs.pop('uploader', '')
        plugins = kwargs.pop('plugins', [])

        if not uploader_name:       # 用户没有指定名字
            # 尝试搜索匹配规则
            matched_rule = self._search_rule(path)
            if matched_rule:
                uploader_name = matched_rule.uploader
                plugins = matched_rule.plugins

        uploader = self.get_uploader(uploader_name)
        method = uploader.upload_method

        for plugin_name in plugins:
            plugin = self._plugins[plugin_name]
            method = plugin(method)

        try:
            return method(path, **kwargs)
        except Exception as err:
            raise UploadError(f'Exception happens when upload: {err}')

    def _save_db(self):
        self._data_path.write_text(json.dumps(self._history_data), encoding='utf-8')

    def _search_rule(self, path: Path) -> Optional[UploadRule]:
        pass

    def _auto_select(self) -> Uploader:
        if self._selected_uploader:
            return self._selected_uploader

        sorted_ups = sorted(self._uploaders.values(),
                            key=lambda x: x.priority)
        for u in sorted_ups:
            if u.available():
                return u
        raise NoAvailableUploaderError()

    def get_uploader(self, name: str = '', available=True) -> Uploader:
        """Return an uploader entity."""
        if name:
            if name not in self._uploaders:
                raise UploaderNotFoundError(f'指定的 Uploader 不存在: {name}')
            uploader = self._uploaders[name]
            if available and not uploader.available():
                raise UploaderNotAvailableError(f'指定的 Uploader 不可用: {name}')
            return uploader
        else:
            return self._auto_select()

    def select(self, name='') -> 'UploaderProxy':
        """Select an uploader entity as the current one."""
        upr = self.get_uploader(name)
        self._selected_uploader = upr
        return self

    def show_history(self):
        print(self._history_data)
        return self._history_data


if __name__ == '__main__':
    up = UploaderProxy(force_init=True)
    print(__file__)
    x = up(__file__, uploader='alioss', plugins=['markdown_link', 'clipboard'])
    print(x)
