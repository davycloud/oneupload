import functools
from abc import ABCMeta, abstractmethod


class Plugin(metaclass=ABCMeta):
    def __init__(self, upload_method):
        self.upload_method = upload_method
        self.__call__ = functools.wraps(self.upload_method)

        self._input_path = None
        self._input_kwargs = None
        self._output = None

    def __call__(self, path, **kwargs):
        self._input_path = path
        self._input_kwargs = kwargs
        self.pre_upload()
        self._output = self.do_upload()
        self.post_upload()
        return self._output

    def pre_upload(self):
        pass

    def post_upload(self):
        pass

    def do_upload(self):
        return self.upload_method(self._input_path,
                                  **self._input_kwargs)


class LoggingPlugin(Plugin):
    def pre_upload(self):
        print('Input: ', self._input_path, self._input_kwargs)

    def post_upload(self):
        print('Output: ', self._output)


class CachePlugin(Plugin):
    def pre_upload(self):
        pass


class MarkdownLinkPlugin(Plugin):
    def post_upload(self):
        url = self._output
        if url.startswith('!['):
            pass
        self._output = f'![]({url})'


class ClipboardPlugin(Plugin):
    def post_upload(self):
        try:
            import pyperclip  # noqa
        except ImportError:
            print('要使用该插件需要安装 pyperclip 模块')
        else:
            pyperclip.copy(self._output)
            print(f'结果已复制到剪切板，使用 Ctrl-V 即可粘贴。')
