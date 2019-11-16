# This is a simple spider project aimmed to crawl company related data.
____

# Intro
A spider system implemented with python currently is released. If don't want to entangled in completed deployment, you can run in `standalone` mode, which also supports multi-task/project multi-thread crawling.

# Steps
## 1. Prepare python execution environment:
```
conda env update -f environment.yaml
```
This command is based on `base` env.
## 2. Configure projects
Populate configuration files for corresponding projects. Refer to `cfg/template_cfg.yml` for details
## 3. Mode
There are `standalone` and `cluster` two modes now. If use cluster mode, please overwrite the project's type with `cluster.master` or `cluster.slave` in `cfg/cfg.yml` for all instances
## 4. Start
Start the task by 
```
cd $ROOT
./scripts/start.sh
```
where `$ROOT` is the root path of `enterprise`.