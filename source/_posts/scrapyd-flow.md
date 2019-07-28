---
title: Scrapyd运行流程总结
date: 2018-07-26 22:35:20
categories: 源码研究 #文章文类
tags: [Scrapyd,源码,python] #文章标签，多于一项时用这种格式
---
### 执行入口
入口程序在Scrapyd源代码的setup.py中指定：
[Github - Scrapyd](https://github.com/scrapy/scrapyd/blob/master/setup.py)
```
    setup_args['entry_points'] = {'console_scripts': [
        # 打包后命令执行入口
        'scrapyd = scrapyd.scripts.scrapyd_run:main'
    ]}
```

从代码可以看到，入口程序：scrapyd/scripts/scrapyd_run.py的main()函数；

```
#!/usr/bin/env python

from twisted.scripts.twistd import run
from os.path import join, dirname
from sys import argv
import scrapyd

# Scrapyd 命令入口
def main():
	# -n：非守护进程方式启动；
	# -y：使用用户指定的application，这里有txapp.py生成application
    argv[1:1] = ['-n', '-y', join(dirname(scrapyd.__file__), 'txapp.py')]
    # 执行twisted.scripts.twistd中的run()函数
    run()

if __name__ == '__main__':
    main()
```
这里是使用twistd命令，参数：【-n；-y】具体功能可以查看twistd -h查看，注释也写清楚了。

### Twisted源码解析

最终执行的是twisted/scripts/twistd.py的run()方法；


```
# -*- test-case-name: twisted.test.test_twistd -*-
# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
The Twisted Daemon: platform-independent interface.

@author: Christopher Armstrong
"""

from __future__ import absolute_import, division

from twisted.application import app

from twisted.python.runtime import platformType
if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions, \
        WindowsApplicationRunner as _SomeApplicationRunner
else:
    from twisted.scripts._twistd_unix import ServerOptions, \
        UnixApplicationRunner as _SomeApplicationRunner

def runApp(config):
    runner = _SomeApplicationRunner(config)
    # 调用twisted.scripts._twistd_unix.UnixApplicationRunner.run()方法
    runner.run()
    if runner._exitSignal is not None:
        app._exitWithSignal(runner._exitSignal)


def run():
	# 直接调用twisted.application.app.run()方法,这里最终调用上面 的runApp(config)方法
    app.run(runApp, ServerOptions)


__all__ = ['run', 'runApp']
```

代码不多，直接贴上了。正如注释中所写，程序最终调用的是UnixApplicationRunner（Linux下）或者WindowsApplicationRunner（Windows下）的run()方法；

下面使用UnixApplicationRunner进行下面的流程。

```
# 启动application
def run(self):
    """
    Run the application.
    """
    # 预处理，检查进程ID，输入输出
    self.preApplication()
    # 获取application，创建or根据用户指定的实例化
    self.application = self.createOrGetApplication()

    self.logger.start(self.application)
    # 启动application & 事件循环
    self.postApplication()
    self.logger.stop()
```

这里createOrGetApplication()方法，就是用来加载前面scrapyd入口脚本中-y指定的txapp.py中的application的，这个到后面启动Service的时候，还会出现。

调用postApplication()启动应用和Twisted的事件循环；

```
def postApplication(self):
    """
    To be called after the application is created: start the application
    and run the reactor. After the reactor stops, clean up PID files and
    such.
    """
    try:
        #启动应用
        self.startApplication(self.application)
    except Exception as ex:
        statusPipe = self.config.get("statusPipe", None)
        if statusPipe is not None:
            message = self._formatChildException(ex)
            untilConcludes(os.write, statusPipe, message)
            untilConcludes(os.close, statusPipe)
        self.removePID(self.config['pidfile'])
        raise
    else:
        statusPipe = self.config.get("statusPipe", None)
        if statusPipe is not None:
            untilConcludes(os.write, statusPipe, b"0")
            untilConcludes(os.close, statusPipe)
    # 启动Twisted事件循环
    self.startReactor(None, self.oldstdout, self.oldstderr)
    self.removePID(self.config['pidfile'])
    
def startApplication(self, application):
    """
    Configure global process state based on the given application and run
    the application.

    @param application: An object which can be adapted to
        L{service.IProcess} and L{service.IService}.
    """
    process = service.IProcess(application)
    if not self.config['originalname']:
        launchWithName(process.processName)
    self.setupEnvironment(
        self.config['chroot'], self.config['rundir'],
        self.config['nodaemon'], self.config['umask'],
        self.config['pidfile'])

    service.IService(application).privilegedStartService()

    uid, gid = self.config['uid'], self.config['gid']
    if uid is None:
        uid = process.uid
    if gid is None:
        gid = process.gid
    if uid is not None and gid is None:
        gid = pwd.getpwuid(uid).pw_gid

    self.shedPrivileges(self.config['euid'], uid, gid)
    # 启动application
    app.startApplication(application, not self.config['no_save'])
```

这里最终还是调用app.startApplication()；

```
def startApplication(application, save):
    from twisted.internet import reactor
    # 这里就启动了twistd的application，application内部会有多个Service&component
    service.IService(application).startService()
    if save:
        p = sob.IPersistable(application)
        reactor.addSystemEventTrigger('after', 'shutdown', p.save, 'shutdown')
    reactor.addSystemEventTrigger('before', 'shutdown',
                                  service.IService(application).stopService)
```

到这个地方，一般正常使用Twisted的应用就是这么启动的。
具体怎么启动（startService）的？这块儿，我纠结的两天时间。

其实，这个地方的Twisted Application是个Componentized mixin，具体还得从上面我们指定的txapp.py看起。

```
# scrapyd/txapp.py

# this file is used to start scrapyd with twistd -y
from scrapyd import get_application
application = get_application()


# scrapyd/__init__.py

import pkgutil

__version__ = pkgutil.get_data(__package__, 'VERSION').decode('ascii').strip()
version_info = tuple(__version__.split('.')[:3])

from scrapy.utils.misc import load_object
from scrapyd.config import Config


def get_application(config=None):
    if config is None:
        config = Config()
    apppath = config.get('application', 'scrapyd.app.application')
    appfunc = load_object(apppath)
    return appfunc(config)
    

```

这个地方最终return的是scrapyd/app.py的Application；这才是Scrapyd的核心实现：

```
from twisted.application.service import Application
from twisted.application.internet import TimerService, TCPServer
from twisted.web import server
from twisted.python import log

from scrapy.utils.misc import load_object

from .interfaces import IEggStorage, IPoller, ISpiderScheduler, IEnvironment
from .eggstorage import FilesystemEggStorage
from .scheduler import SpiderScheduler
from .poller import QueuePoller
from .environ import Environment
from .config import Config

def application(config):
    app = Application("Scrapyd")
    # 监听端口
    http_port = config.getint('http_port', 6800)
    # 绑定IP地址
    bind_address = config.get('bind_address', '127.0.0.1')
    # TimerService的轮询间隔
    poll_interval = config.getfloat('poll_interval', 5)

    # 队列 -- 每个project一个队列
    poller = QueuePoller(config)
    # 打包 & 部署后的egg路径
    eggstorage = FilesystemEggStorage(config)
    # 调度器
    scheduler = SpiderScheduler(config)
    # 环境变量
    environment = Environment(config)

    # Application是Componentized mixin，可以set很多组件
    app.setComponent(IPoller, poller)
    app.setComponent(IEggStorage, eggstorage)
    app.setComponent(ISpiderScheduler, scheduler)
    app.setComponent(IEnvironment, environment)

    # launcher 具体启停Spider等，执行相应的命令
    laupath = config.get('launcher', 'scrapyd.launcher.Launcher')
    laucls = load_object(laupath)
    launcher = laucls(config, app)

    webpath = config.get('webroot', 'scrapyd.website.Root')
    webcls = load_object(webpath)

    # 每5秒钟 从队列虫取出已经schedule到队列中的Spider执行
    timer = TimerService(poll_interval, poller.poll)
    # web服务，接收web请求，包括查看log，启动Spider，列出所有project等等。。。
    webservice = TCPServer(http_port, server.Site(webcls(config, app)), interface=bind_address)
    log.msg(format="Scrapyd web console available at http://%(bind_address)s:%(http_port)s/",
            bind_address=bind_address, http_port=http_port)

    # 这里是重点了，setServiceParent将app设置为自身的parent，同时会调用自身的startService()方法（因为launcher、timer、webservice都是IService的），这样每个Service都启动了。
    # 这个地方纠结的两天。。。
    launcher.setServiceParent(app)
    timer.setServiceParent(app)
    webservice.setServiceParent(app)

    return app
```
### Scrapyd的核心实现
主要包括以3个主要服务：
- Launcher
    - 主要功能是执行调度任务，从Poller中获取已经调度的任务并执行
- TCPServer
    - 主要提供Web服务，通过Http接收请求。包括Job、Schedule、Logs等等
- TimerService
    - 周期执行（5s），主要功能是从Web Server接收的调度任务中，每次每个project调度一个任务给Launcher执行

以及下面两个辅助的数据结构：

- Poller
    - 对队列使用的一层抽象
- SqliteSpiderQueue
    - 使用Sqlite作为队列底层存储的抽象

![Scrapyd流程](scrapyd_flow.jpg)

为了方便理解，看代码理解的时候总结了一张思维导图，如导图中所描述的，这样Scrapyd的三个核心服务，组成一个任务环，中间通过Poller和SqliteSpiderQueue两个辅助数据结构，实现类似生产者消费者模式。

这就是Scrapyd的核心实现，实现简单日志监控、任务调度、项目发布等基本功能接口。解决了Scrapy使用过程中的部分痛点。
由于Scrapyd使用还是面向程序员，管理控制台比较简陋且功能不完善，所以才有Gerapy出现了，可以在管理控制台上实现项目发布、启动Spider等等。但Gerapy做的也不太完善，比如周期性调度Spider等没有实现，可能在开发中。。。