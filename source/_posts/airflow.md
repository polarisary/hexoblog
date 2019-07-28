---
title: Airflow安装使用
date: 2018-06-29 22:31:21
categories: 工具
tags: [airflow,crontab]
---
### 介绍
Airflow 是 Airbnb 使用Python开发的用于工作流管理的开源项目，简单说就是管理和调度定时任务，可以替代Linux的crontab。如果你的crontab很多，不好管理，那么airflow对你来说就是救星。它自带简洁的UI，现在 Apache 下做孵化，地址是https://github.com/apache/incubator-airflow

### 安装
>  由于airflow是使用Python开发的，所以要安装airflow，需要Python环境，Python2 或者Python3都可以。
>  最好使用VirtualEnv来安装，因为airflow可能依赖了一些Python库和你的Python环境中的某个库的版本冲突，我就是因为这个搞了差不多一天时间。

安装好Python环境和virtualenv后，开始安装airflow
```
# 1）首先创建并进入airflow的工作目录下
$ cd /path/to/my/airflow/workspace
$ virtualenv -p `which python3` venv
$ source venv/bin/activate
(venv) $ 
#  2）安装airflow
(venv) $ pip install airflow
# 3）设置AIRFLOW_HOME
(venv) $ cd /path/to/my/airflow/workspace
(venv) $ mkdir airflow_home
(venv) $ export AIRFLOW_HOME=`pwd`/airflow_home
# 4）测试airflow
(venv) $ airflow version
# 5）初始化airflow数据库，默认airflow使用SQLite，线上环境可以使用mysql
(venv) $ airflow initdb
# 6）启动airflow webserver，airflow默认监听8080端口，Web Server启动后，就可以通过IP:Port(8080)访问了。
(venv) $ airflow webserver
```
### 创建DAG
1）在airflow_home中创建dags目录，目录结构如下：
```
(venv) ➜  airflow_home tree
.
├── airflow.cfg
├── airflow.db
├── airflow-webserver.pid
├── dags
│   ├── hello_world.py
│   └── __pycache__
│       └── hello_world.cpython-36.pyc
├── logs
│   ├── hello_world
│   │   ├── dummy_task
```
2）的dags目录下，创建一个dag，hello_world.py
```
from datetime import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator

def print_hello():
    print ("Hello World...")
    return 'Hello world!'

dag = DAG('hello_world', description='Simple tutorial DAG',
        schedule_interval='*/1 * * * *',
        start_date=datetime(2018, 6, 29), catchup=False)

dummy_operator = DummyOperator(task_id='dummy_task', retries=3, dag=dag)

hello_operator = PythonOperator(task_id='hello_task', python_callable=print_hello, dag=dag)

dummy_operator >> hello_operator
```
### 启动DAG
```
(venv) $ airflow scheduler
```
![Airflow控制台](airflow.jpg)
访问URL【http://ip:8080/admin/】就可以看到上图airflow控制台，里面很多默认的dag，也有我们刚才创建hello_world DAG也在里面，但需要点击红框里的按钮，airflow才会调度dag执行。

### AirFlow相关命令
```
# print the list of active DAGs
airflow list_dags
# prints the list of tasks the "tutorial" dag_id
airflow list_tasks tutorial
# prints the hierarchy of tasks in the tutorial DAG
airflow list_tasks tutorial --tree
# 以debug模式，deamon方式运行web server
airflow webserver --debug &

 ### 测试DAG
# testing print_date
airflow test hello_world hello_task 2018-06-29
```
### 参考资料
[Apache Airflow (incubating) Documentation](https://airflow.incubator.apache.org/index.html)
[Get started developing workflows with Apache Airflow](http://michal.karzynski.pl/blog/2017/03/19/developing-workflows-with-apache-airflow/)
[使用 airflow 替代你的 crontab](http://sanyuesha.com/2017/11/13/airflow/)