import json
import base64
import hashlib
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen, build_opener, Request
from pathlib import Path


def github_sha(content):
    """Generate SHA hashes

    See:
    https://stackoverflow.com/questions/7225313/how-does-git-compute-file-hashes
    """
    head = f'blob {len(content)}\0'.encode()
    return hashlib.sha1(head + content).hexdigest()


class GitHub:
    def __init__(self, owner, repo, token, path=''):
        self.owner = owner
        self.token = token
        self.repo = repo
        self.path = path.strip()  # 默认的存储路径
        if self.path and not self.path.endswith('/'):
            self.path += '/'
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': 'token ' + self.token
        }
        self._opener = build_opener()
        self._opener.addheaders = list(self.headers.items())

    @property
    def unique_id(self) -> str:
        return f'github/{self.owner}/{self.repo}'

    def _request(self, url, data=None, headers=None, method='GET'):
        headers = headers or self.headers
        if data is not None:
            if not isinstance(data, (str, bytes)):
                data = urlencode(data)
            if not isinstance(data, bytes):
                data = data.encode('ascii')
        req = Request(url, data=data, headers=headers, method=method.upper())
        res = urlopen(req)
        return json.load(res) if res else {}

    def get(self, url):
        return self._request(url)

    def put(self, url, data):
        return self._request(url, data, method='PUT')

    def get_content(self, path):
        url = f'https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}'
        return self.get(url)

    def create_or_update_content(self, path, content, message=None, sha=None):
        url = f'https://api.github.com/repos/{self.owner}/{self.repo}/contents/{path}'
        if message is None:
            if sha:
                message = f'Update {path}'
            else:
                message = f'Create {path}'
        body = {'message': message, 'content': content, 'sha': sha}
        return self.put(url, data=json.dumps(body))

    def _gh_path(self, filename):
        return self.path + filename

    def upload_content(self, path, content, message=None, overwrite=True, **kwargs):
        if not isinstance(content, bytes):
            content = content.encode()
        content_sha = github_sha(content)
        content = base64.b64encode(content).decode()
        try:
            self.create_or_update_content(path, content, message=message)
        except HTTPError as err:
            if err.code == 422:
                sha = self.get_content(path)['sha']
                if sha == content_sha:
                    print(f"{path} already exist and has the same content, pass.")
                elif overwrite:
                    self.create_or_update_content(path, content,
                                                  message=message,
                                                  sha=sha)
            else:
                raise

    def upload(self, path, rename=None, cdn=False, overwrite=True):
        path = Path(path)
        if rename:
            if isinstance(rename, str):
                remote_name = rename
            elif callable(rename):
                remote_name = rename(path)
            else:
                raise ValueError("rename is a function or str.")
        else:
            remote_name = path.name
        message = f"upload {remote_name}"
        gh_path = self._gh_path(remote_name)
        self.upload_content(gh_path, path.read_bytes(), message, overwrite=overwrite)
        if cdn:
            return self.cdn(gh_path)
        else:
            # return f"https://github.com/{self.owner}/{self.repo}/main/{gh_path}"
            return f'https://raw.githubusercontent.com/{self.owner}/{self.repo}/main/{gh_path}'

    def cdn(self, path: str):
        return f"https://cdn.jsdelivr.net/gh/{self.owner}/{self.repo}@main/{path}"
