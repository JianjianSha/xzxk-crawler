import os
import importlib
import yaml
from multiprocessing import Process
from .config import load


class Task(Process):
    def __init__(self, name, value):
        super(Task, self).__init__()
        mod = importlib.import_module('projects.'+name)
        cls_ = getattr(mod, 'Crawler')
        self.instance = cls_()
        self.state = value.state

    def run(self):
        if self.state == 1:
            self.instance.run()

    # def __call__(self, *args):
    #     self.run()

class TaskContainer:
    def __init__(self):
        cfg_file = os.path.realpath(
            os.path.join(os.path.dirname(__file__), '../cfg', 'cfg.yml'))
        self.cfg = load(cfg_file)
        self.tasks = {}
        for k in self.cfg.PROJECTS:
            v = self.cfg.PROJECTS[k]
            if not v.state:
                continue
            if k not in self.tasks:
                self.tasks[k] = Task(k, v)

    def start(self):
        for k in self.tasks:
            task = self.tasks[k]
            task.start()
            
        for k in self.tasks:
            task = self.tasks[k]
            task.join()

