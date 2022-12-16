import shlex
import subprocess

from pathlib import Path
from string import Template
from urllib.parse import quote


def upload_factory(cmd_template: str,
                   url_template: str):

    cmd_template = shlex.join(shlex.split(cmd_template))

    ct = Template(cmd_template)
    ut = Template(url_template)

    def upload(path, **kwargs):
        path = Path(path)
        if not path.is_file():
            print(f'{path} 文件不存在！')
            return
        rename = kwargs.pop('rename', '')
        command = ct.substitute(file_path=path.as_posix(), rename=rename)
        print(shlex.split(command))
        subprocess.run(shlex.split(command))

        if rename:
            name = rename
        else:
            name = path.name
        return ut.substitute(name=quote(name))
    return upload
