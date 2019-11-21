import os
import importlib
import yaml
from multiprocessing import Process, Value
from .config import load
from .utils.env import IS_WINDOWS
import signal
import time





class Task(Process):
    def __init__(self, name, type, alive):
        super(Task, self).__init__()
        mod = importlib.import_module('tasks.'+name)
        if type == 'standalone':
            cls_ = getattr(mod, 'Crawler')
            self.instance = cls_()
        else:
            cls_ = getattr(mod, 'DCrawler')
            self.instance = cls_(type.split('.')[-1] == 'master')
        self.alive = alive

    def run(self):
        self.instance.run(self.alive)

    # def __call__(self, *args):
    #     self.run()

def task_Win(name, type, alive):
    mod = importlib.import_module('tasks.'+name)
    if type == 'standalone':
        cls_ = getattr(mod, 'Crawler')
        instance = cls_()
    else:
        cls_ = getattr(mod, 'DCrawler')
        instance = cls_(type.split('.')[-1] == 'master')

    instance.run(alive)


class TaskContainer:
    def __init__(self):
        cfg_file = os.path.realpath(
            os.path.join(os.path.dirname(__file__), '../cfg', 'cfg.yml'))
        self.cfg = load(cfg_file)
        self.alive = Value('b', True)
        self.tasks = []

        for k in self.cfg.TASKS:
            v = self.cfg.TASKS[k]
            if not v.ACTIVE:
                continue

            if IS_WINDOWS:
                task = Process(target=task_Win, args=(k, v.TYPE, self.alive))
            else:
                task = Task(k, v.TYPE, self.alive)
            self.tasks.append(task)

    def start(self):
        for task in self.tasks:
            task.daemon = True
            task.start()
            
        try:
            flag = True
            while flag:
                for task in self.tasks:
                    if task.is_alive():
                        break
                else:                   # all tasks terminated
                    flag = False    

        except KeyboardInterrupt as e:
            self.alive.value = False
            print('interrupt by user')




