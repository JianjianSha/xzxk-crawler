import execjs.runtime_names
import os


class js_ctx:
    def __init__(self, *files, workspace=None):
        self.workspace = workspace
        self.files = files
        assert len(files) > 0

    def __enter__(self):
        for i in range(len(self.files)):
            with open(self.files[i], mode='r', encoding='utf-8') as f:
                if i == 0:
                    content = f.read()
                else:
                    content += f.read()
        return execjs.get(execjs.runtime_names.Node).compile(content, cwd=self.workspace)

    def __exit__(self, *args):
        pass

    # def __call__(self, fname, *args):
    #     print('call js metod', fname)
    #     return self.ctx.call(fname, *args)


            