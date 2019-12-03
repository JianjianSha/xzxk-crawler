from framework.task import TaskContainer
from tasks.zj.nb_sync import Sync as ZJNBSync


if __name__ == '__main__':
    # crawling task
    # container = TaskContainer()
    # container.start()

    # sync task
    s = ZJNBSync()
    s.run()