# noinspection SpellCheckingInspection
DEFAULT_CONFIG = {
    'client': {
        'alioss': {
            'path': 'oneupload.clients.alioss:AliOSS',
        },
        'github': {
            'path': 'oneupload.clients.github:GitHub',
        },
        'command': {
            'path': 'oneupload.clients.command:upload_factory',
        }
    },
    'plugin': {
        'logging': 'oneupload.plugin:LoggingPlugin',
        'markdown_link': 'oneupload.plugin:MarkdownLinkPlugin',
        'clipboard': 'oneupload.plugin:ClipboardPlugin'
    }
}

INIT_CONFIG_TEXT = """
# 配置上传客户端
#
#

# [uploader.alioss]
# 
# client = 'alioss'
# 
# Endpoint = "<YOUR ENDPOINT>"
# Access_Key = "<YOUR ACCESS KEY ID>"
# Access_Secret = "<YOUR ACCESS KEY SECRET>"
# Bucket = "<YOUR BUCKET NAME>"

# [uploader.github]
# 
# client = 'github'
# 
# owner = "<YOUR USERNAME>"
# token = "<YOUR GITHUB TOKEN>"
# repo  = "<YOUR REPO NAME>"

# [uploader.ossutil]
# 
# client = 'command'
# priority = 1
# 
# cmd_template = 'ossutil64.exe cp ${file_path} oss://my-bucket/ -f -u'
# url_template = 'https://my-bucket.oss-cn-hangzhou.aliyuncs.com/${name}'

# [[cases]]
# 
# match = '*.png'
# 
# [[cases]]
# 
# match = '*.md'

"""
