import os
import importlib
import yaml
from multiprocessing import Process
from .config import load
import platform

IS_WINDOWS = (platform.system() == 'Windows')
IS_LINUX = (platform.system() == 'Linux')


class Task(Process):
    def __init__(self, name):
        super(Task, self).__init__()
        mod = importlib.import_module('projects.'+name)
        cls_ = getattr(mod, 'Crawler')
        self.instance = cls_()

    def run(self):
        self.instance.run()

    # def __call__(self, *args):
    #     self.run()

def task_Win(name):
    mod = importlib.import_module('projects.'+name)
    cls_ = getattr(mod, 'Crawler')
    instance = cls_()
    instance.run()


class TaskContainer:
    def __init__(self):
        cfg_file = os.path.realpath(
            os.path.join(os.path.dirname(__file__), '../cfg', 'cfg.yml'))
        self.cfg = load(cfg_file)
        self.tasks = 
        for k in self.cfg.PROJECTS:
            v = self.cfg.PROJECTS[k]
            if not v.state:
                continue
            
            if IS_WINDOWS:
                task = Process(target=task_Win, args=(k,))
            else:
                task = Task(k)
            self.tasks.append(task)

    def start(self):
        for task in self.tasks:
            task.start()
            
        for task in self.tasks:
            task.join()

