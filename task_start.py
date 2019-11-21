from framework.task import TaskContainer


if __name__ == '__main__':
    container = TaskContainer()
    container.start()




    # temporary test code
    # from framework.utils.js_wrapper import js_ctx
    # ctx = js_ctx('./log/readme.md', './log/court.ws.log')
    # for file in ctx.files:
    #     print(file)
    # with open('./log/readme.md', 'r', encoding='utf-8') as f:
    #     content = f.read()
    # with open('./log/court.ws.log', 'r', encoding='utf-8') as f:
    #     content += f.read()

    # print(type(content))
    # print(content)