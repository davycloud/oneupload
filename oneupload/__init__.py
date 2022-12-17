"""One upload for many storages.

"""
from .proxy import UploaderProxy


__version__ = '0.0.3'

upload = UploaderProxy()
