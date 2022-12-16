# oneupload

只提供一个上传接口：`upload`，对接多个存储平台。

主要用于 Markdown 写作时的附件（主要是图片）上传。

```python
from oneupload import upload

upload('a_pic.png')
```

使用配置文件来控制到底把文件上传到哪里。


