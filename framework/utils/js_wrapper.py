import execjs.runtime_names
import os


class js_ctx:
    def __init__(self, file):
        self.file = file

    def __enter__(self):
        with open(self.file, encoding='utf-8') as f:
            self.f = f.read()
        return execjs.get(execjs.runtime_names.Node).compile(self.f)

    def __exit__(self, *args):
        pass

    # def __call__(self, fname, *args):
    #     print('call js metod', fname)
    #     return self.ctx.call(fname, *args)


            