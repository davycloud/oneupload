import hashlib
import os
import sys
import uuid
import importlib
from pathlib import Path

from typing import Dict


WIN = sys.platform.startswith("win")


def _posixify(name: str) -> str:
    return "-".join(name.split()).lower()


# copy from click
def get_app_dir(app_name: str, roaming: bool = True, force_posix: bool = False) -> str:
    r"""Returns the config folder for the application.  The default behavior
    is to return whatever is most appropriate for the operating system.

    To give you an idea, for an app called ``"Foo Bar"``, something like
    the following folders could be returned:

    Mac OS X:
      ``~/Library/Application Support/Foo Bar``
    Mac OS X (POSIX):
      ``~/.foo-bar``
    Unix:
      ``~/.config/foo-bar``
    Unix (POSIX):
      ``~/.foo-bar``
    Windows (roaming):
      ``C:\Users\<user>\AppData\Roaming\Foo Bar``
    Windows (not roaming):
      ``C:\Users\<user>\AppData\Local\Foo Bar``

    :param app_name: the application name.  This should be properly capitalized
                     and can contain whitespace.
    :param roaming: controls if the folder should be roaming or not on Windows.
                    Has no affect otherwise.
    :param force_posix: if this is set to `True` then on any POSIX system the
                        folder will be stored in the home folder with a leading
                        dot instead of the XDG config home or darwin's
                        application support folder.
    """
    if WIN:
        key = "APPDATA" if roaming else "LOCALAPPDATA"
        folder = os.environ.get(key)
        if folder is None:
            folder = os.path.expanduser("~")
        return os.path.join(folder, app_name)
    if force_posix:
        return os.path.join(os.path.expanduser(f"~/.{_posixify(app_name)}"))
    if sys.platform == "darwin":
        return os.path.join(
            os.path.expanduser("~/Library/Application Support"), app_name
        )
    return os.path.join(
        os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
        _posixify(app_name),
    )


def import_module(path: str):
    # path = 'oneupload.clients.alioss:AliOSS'
    mod_attr = path.rsplit(':', 1)
    if len(mod_attr) == 2:
        mod_name, attr_name = mod_attr
    else:
        mod_name, attr_name = mod_attr[0], None
    mod = importlib.import_module(mod_name)
    if attr_name:
        try:
            attr = getattr(mod, attr_name)
        except AttributeError as e:
            raise ImportError(str(e))
    else:
        attr = None
    return mod, attr


def md5(path: Path):
    md = hashlib.md5()
    md.update(path.read_bytes())
    return md.hexdigest()


def unique_id(ns: uuid.UUID, name: str, data: Dict):
    data_text = ','.join([f"{k}={v}" for k, v in sorted(data.items())])
    uid = uuid.uuid3(ns, name + data_text)
    length = len(name) + 13
    return f'{name}:{uid}'[:length]


if __name__ == '__main__':
    ns = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    print(unique_id(ns, 'abc', {'b': 2, 'a': 1}))
