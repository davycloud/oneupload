"""Aliyun OSS Client

需要先安装依赖:
    pip install oss2

"""
from pathlib import Path
import oss2


class AliOSS:
    def __init__(self, access_key, access_secret,
                 bucket, endpoint, path='test'):
        """

        :param access_key: <Access Key ID>
        :param access_secret: <Access Key Secret>
        :param bucket: <Bucket>
        :param endpoint: oss-cn-shanghai.aliyuncs.com
        :param path: 存储路径，默认为空
        """
        auth = oss2.Auth(access_key, access_secret)
        self.bucket = oss2.Bucket(auth, endpoint, bucket)
        if path and not path.endswith('/'):
            path += '/'
        self.content_path = path
        if endpoint.startswith('http://'):
            self._host = endpoint[7:]
        elif endpoint.startswith('https://'):
            self._host = endpoint[8:]
        else:
            self._host = endpoint
        self.bucket_name = self.bucket.bucket_name

    @property
    def unique_id(self) -> str:
        return f'{self.bucket_name}.{self._host}'

    def upload(self, local_file, rename=None):
        local_file = Path(local_file)
        if rename:
            if isinstance(rename, str):
                remote_name = rename
            elif callable(rename):
                remote_name = rename(local_file)
            else:
                raise ValueError("rename must be a function or str.")
        else:
            remote_name = local_file.name
        remote_name = remote_name.replace(' ', '-')

        key = self.content_path + remote_name
        content = local_file.read_bytes()
        self.upload_content(key, content)
        return f"https://{self.bucket_name}.{self._host}/{key}"

    def upload_content(self, key, content):
        self.bucket.put_object(key, content)

    def list_objects(self):
        # Traverse all objects in the bucket
        for object_info in oss2.ObjectIterator(self.bucket):
            print(object_info.key)

    def match(self, url):
        return url.startswith(f'https://{self.bucket_name}')
