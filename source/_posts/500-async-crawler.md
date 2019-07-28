---
title: 500-async-crawler
date: 2018-12-13 20:17:05
categories: 500 Lines or Less
tags: [asyncio,python,crawler]
---

# 原文&作者：

[A Web Crawler With asyncio Coroutines](http://aosabook.org/en/500L/a-web-crawler-with-asyncio-coroutines.html)

- A. Jesse Jiryu Davis

> A. Jesse Jiryu Davis是纽约MongoDB的高级工程师，负责MongoDB的异步Python驱动，也是MongoDB C驱动的主程，同时也是PyMongo团队的一员。并且在 asyncio和Tornado上都所有贡献。他的个人博客地址是：http://emptysqua.re


- Guido van Rossum

> Guido van Rossum是Python之父，Python社区称他为BDFL，博客地址：http://www.python.org/~guido/

# 简介
传统的计算机科学，强调高效算法、整个计算越快越好。但很多网络程序耗时并不在计算上，而是保持很多慢连接，或者很少的事件上。这些程序面临一个完全不一样的挑战：需要等待大量的有效网络事件。当前解决的方法是使用异步IO

本章介绍一个简单的网络爬虫，这是一个原生的异步应用程序，因为它等待很多网络请求返回，但计算量很少。每次请求的网页数越多，完成的越快。如果每个请求一个线程，随着并发请求的增加，将会耗尽内存或者跟线程相关的资源。使用异步I/O可以避免线程的弊端。

我们将分三个阶段来完成这个爬虫。首先，我们简单介绍下异步事件循环，使用事件循环和回调来实现一个简单的爬虫。这种方式非常高效，但扩展到较复杂的问题上将陷入回调陷阱。接下来，我们介绍高效并且可扩展的Python协程，我们使用生成器来实现简单的协程。最后，我们将使用Python标准库asyncio，并配合异步队列来实现爬虫

# 任务

网络爬虫在网络上寻找并下载网页，之后归档或者索引下载下来的网页。从一个根url开始，下载、解析网页中的链接地址，未抓取过的添加到队列继续抓取，直到抓取的网页上的链接地址都抓取过了，并且队列为空爬虫停止。

我们可以同时下载多个网页来加速爬虫。当爬虫获取到新的链接时，在独立的socket上触发相同的抓取操作，解析相应，并将新的链接地址放入队列中。但可能会因为并发太多而造成性能下降，所以，我们需要限制并发请求数。

# 传统的方法

怎样让爬虫并发起来呢？传统的方式是使用线程池。每个线程每次负责下载一个网页。例如下面的程序，从xkcd.com下载网页：
```
def fetch(url):
    sock = socket.socket()
    sock.connect(('xkcd.com', 80))
    request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(url)
    sock.send(request.encode('ascii'))
    response = b''
    chunk = sock.recv(4096)
    while chunk:
        response += chunk
        chunk = sock.recv(4096)

    # Page is now downloaded.
    links = parse_links(response)
    q.add(links)
```
socket默认是阻塞的（当线程调用connect、recv等方法，程序将等待方法返回）。所以要同时下载多个网页，需要多线程。复杂的应用程序将使用线程池来减少线程频繁创建的开销，重复利用空闲的线程。在socket上的连接池也是同样的道理。

并且，线程开销比较大，操作系统对用户或者机器的线程数是有明确限制的。Jesse的操作系统，Python线程占用50k内存，如果开启成千上万的线程将使系统崩溃。如果我们同时启动成千上万的下载操作在socket上，结果是在socket耗尽之前，线程所占资源将首先到达瓶颈。

著名的 "C10K问题"，Dan Kegel 列出了多线程并发的限制。他这样说：
>
> It's time for web servers to handle ten thousand clients simultaneously, don't you think? After all, the web is a big place now.

Kegel在1999年提出“C10K”，现在看来并发1万不是什么特别困难的问题，但是这个问题仅仅在并发数量上改变了，本质上来说，没有改变。在当时，一个线程处理处理一个连接解决1万并发是不切实际的。现在应该解决并发数量上高一个量级了。的确，我们的网络爬虫可以使用线程实现。但是，大规模的应用，成千上万的并发连接，c10k问题还是存在的，即使socket没有超过大多数操作系统限制，线程也耗尽了。怎么解决这个问题呢？

# 异步
异步I/O使用非阻塞的套接字，在单线程下实现并发操作。我们的异步爬虫，我们将使用非阻塞套接字：
```
sock = socket.socket()
sock.setblocking(False)
try:
    sock.connect(('xkcd.com', 80))
except BlockingIOError:
    pass
```
不幸的是，非阻塞套接字即使运行正常，也在connect上抛出了异常。这个异常重复底层C函数令人厌恶的行为，它通过将errno设置为EINPROGRESS来告诉你开始运行。

现在，我们需要知道连接什么时候建立成功了，接着可以发送HTTP请求。我们可以简单的通过循环来探测是否建立了连接。

```
request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(url)
encoded = request.encode('ascii')

while True:
    try:
        sock.send(encoded)
        break  # Done.
    except OSError as e:
        pass

print('sent')
```
这种方式不仅浪费CPU资源，而且不能有效的获取多个套接字上的事件。老的BSD Unix操作系统是通过select系统调用来解决这个问题的。他是一个在非阻塞套接字上等待事件的C函数。如今，在大量并发量级的网络应用驱使下，使用poll代替select，接着，BSD操作系统下的kqueue和Linux操作系统下的epoll也相继出现。他们都跟select相似，但在高并发的情况下，性能较好。

Python3.4中的DefaultSelector会根据操作系统选择性能最好的select函数（select、poll或者epoll，kqueue）。为了注册网络I/O事件通知，我们创建了一个非阻塞的套接字并使用默认selector注册。

```
from selectors import DefaultSelector, EVENT_WRITE

selector = DefaultSelector()

sock = socket.socket()
sock.setblocking(False)
try:
    sock.connect(('xkcd.com', 80))
except BlockingIOError:
    pass

def connected():
    selector.unregister(sock.fileno())
    print('connected!')

selector.register(sock.fileno(), EVENT_WRITE, connected)
```

我们忽略错误信息，并且调用selector.register，传入套接字文件描述符和事件类型常量。当连接建立了我们会收到通知，参数EVENT_WRITE：代表我们想知道什么套接字可写。方法参数connected是注册的回调函数，当事件发生时会执行。

我们在一个循环中处理selector获取到的I/O事件通知：
```
def loop():
    while True:
        events = selector.select()
        for event_key, event_mask in events:
            callback = event_key.data
            callback()
```
connected回调函数保存在event_key.data中，当我们收到非阻塞套接字连接建立之后立即执行connected回调函数。

不同于前面的循环，select系统调用会阻塞，等待I/O事件发生。事件循环接着执行通知事件的回调函数。没有完成的事件将保持挂起，等待下一次事件循环执行。

我们已经介绍了哪些内容？我们介绍了怎么开始一个操作，并且在事件准备好后，并且执行其回调函数；我们也介绍了一个异步框架，使用非阻塞套接字和事件循环，在单线程中执行并发操作。

我们已经实现了“并发”，但不是传统意义上的“并行”。也就是说，我们构建了一个可以执行并发I/O的小系统，他可以在其他I/O操作正在执行时，启动新的操作。实际上，他不能利用多核进行并行计算。但是，这个系统是为I/O密集型问题设计的，而不是CPU密集型问题设计的。

所以，我们的事件循环在并发I/O问题上是高效的，因为它不需要为每个连接浪费线程资源。但是，在我们继续之前，纠正一个误解：异步比多线程快。的确，通常在Python中，像我们这样的事件循环在处理少量活动连接的情况下，异步是比多线程稍微慢些，并且，运行时没有GIL的情况下，同样的负载下多线程可能更快。异步适用于事件很少，并有大量慢连接或不活跃连接的应用

# 回调编程
怎么使用我们构建的简洁的框架来实现网络爬虫呢？即使仅仅一个简单的url请求获取，实现起来都很痛苦。

从设置全局变量urls_todo，和seen_urls开始：
```
urls_todo = set(['/'])
seen_urls = set(['/'])
```
其中，seen_urls包括urls_todo和已经完成的url。这两个变量被初始化成根URL（'/'）。
请求一个网页需要一系列的回调。当套接字connected的时候会触发connected回调，并发送get请求到服务端。但是，当需要等待一个返回时，需要注册另一个回调。如果这个回调触发了，才能读取全部的返回结果，这样循环往复的注册回调。

我们把这些回调设计到一个Fetcher对象中。他需要一个URL，一个套接字对象和一个变量来存放返回结果。
```
class Fetcher:
    def __init__(self, url):
        self.response = b''  # Empty array of bytes.
        self.url = url
        self.sock = None
```
我们调用的是Fetcher.fetch函数
```
# Method on Fetcher class.
    def fetch(self):
        self.sock = socket.socket()
        self.sock.setblocking(False)
        try:
            self.sock.connect(('xkcd.com', 80))
        except BlockingIOError:
            pass

        # Register next callback.
        selector.register(self.sock.fileno(),
                          EVENT_WRITE,
                          self.connected)
                          
```
fetch函数首先建立一个socket连接，并声明为非阻塞，通知套接字方法在连接建立之前立刻返回，将控制流程交给事件循环等待连接。下面解析下为什么。假设我们按下面的结构构件应用程序：
```
# Begin fetching http://xkcd.com/353/
fetcher = Fetcher('/353/')
fetcher.fetch()

while True:
    events = selector.select()
    for event_key, event_mask in events:
        callback = event_key.data
        callback(event_key, event_mask)
```
调用select系统函数所有的事件通知都会在事件循环中被处理。之后，fetch函数将控制权交还给事件循环。当事件循环执行上面Fetcher中注册的connected回调函数时，应用程序这才知道socket建立完成了。

下面是connected回调函数的实现：
```
# Method on Fetcher class.
    def connected(self, key, mask):
        print('connected!')
        selector.unregister(key.fd)
        request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(self.url)
        self.sock.send(request.encode('ascii'))

        # Register the next callback.
        selector.register(key.fd,
                          EVENT_READ,
                          self.read_response)
```
connected函数发送一个Get请求。真实的应用将会检查返回值，假设全部的消息一次发送不完。但是我们的请求很小，并且我们的应用是正常的应用程序（无恶意）。所以，我们的应用直接调用send函数，然后等待返回结果。当然，他需要注册另外一个回调函数并将控制权交还给事件循环。最后一个回调函数read_response，处理服务端返回：

```
# Method on Fetcher class.
    def read_response(self, key, mask):
        global stopped

        chunk = self.sock.recv(4096)  # 4k chunk size.
        if chunk:
            self.response += chunk
        else:
            selector.unregister(key.fd)  # Done reading.
            links = self.parse_links()

            # Python set-logic:
            for link in links.difference(seen_urls):
                urls_todo.add(link)
                Fetcher(link).fetch()  # <- New Fetcher.

            seen_urls.update(links)
            urls_todo.remove(self.url)
            if not urls_todo:
                stopped = True
```
这个回调函数将在selector检测到套接字是“readable”可读状态是被触发执行，这意味着两种可能的事情：一是套接字上的数据准备好了，另一个是套接字被关闭了。

这个回调函数在准备好数据的套接字上读取1个chunk大小的数据（chunk小于等于4k），如果套接字上的数据大于4k，那么这次只读取4k，并且套接字保持readable状态，等待下次事件循环调度触发。当返回完成，服务端关闭套接字，并且返回空。

parse_links方法没有介绍，他返回URL集合。每个URL实例化一个Fetcher实例，不存在并发的情况。

注意使用带回调的异步编程的一个特点：在修改共享数据时不需要使用互斥，例如，我们对seen_urls添加元素。多任务没有抢占机制，所以，我们不能在代码中任意地方中断。

我们添加一个stopped全局变量来控制事件循环：
```
stopped = False

def loop():
    while not stopped:
        events = selector.select()
        for event_key, event_mask in events:
            callback = event_key.data
            callback()
```
当所有网页都下载完成，Fetcher将停止全局的事件循环，然后程序退出。

这个例子使用面条式的写法使得异步程序看起来很简单。我们接下来要增加一些计算和I/O操作，并且调度这些操作并发执行。但不使用线程，这些操作也不能实现在一个函数中：当一个函数开始执行I/O操作，说明需要保持一个状态，并且将来会使用到，然后返回，你的职责是思考并且实现这个状态保持的程序。

解释下这是什么意思呢？想想看，使用传统的阻塞I/O在线程中实现抓取一个URL是多么简单啊！
```
# Blocking version.
def fetch(url):
    sock = socket.socket()
    sock.connect(('xkcd.com', 80))
    request = 'GET {} HTTP/1.0\r\nHost: xkcd.com\r\n\r\n'.format(url)
    sock.send(request.encode('ascii'))
    response = b''
    chunk = sock.recv(4096)
    while chunk:
        response += chunk
        chunk = sock.recv(4096)

    # Page is now downloaded.
    links = parse_links(response)
    q.add(links)
```
这个函数在不同套接字之间保存什么状态了？他保持有socket，url和累计的返回结果。传统线程中函数保存状态在堆栈的临时变量中。这个函数有一个“continuation”：会在I/O完成之后执行。运行时环境使用线程的指令指针来保存这个“continuation”。你不需要考虑在I/O完成之后重新保存这些本地变量和“continuation”，他是编程语言内置的功能。

但是，基于回调的异步框架，这些编程语言的内置功能作用也不大。等待I/O时，函数需要明确保存状态，因为，在I/O完成之前函数就返回并且失去了他的栈帧。在我们基于回调的例子中，我们不使用本地变量，而是使用Fetcher的实例变量来保存sock和response。我们不使用指令指针，而是注册connected和read_response回调函数来保存“continuation”。随着应用功能的增加，我们需要手动通过回调保存的状态也越来越复杂。如此繁重的记账式的实现让开发者头疼。

更糟糕的，在回调链在调度到下一个回调之前抛出了异常会发生什么？也就是说，我们在parse_links函数上实现的不好，解析某些页面时抛出了异常：
```
Traceback (most recent call last):
  File "loop-with-callbacks.py", line 111, in <module>
    loop()
  File "loop-with-callbacks.py", line 106, in loop
    callback(event_key, event_mask)
  File "loop-with-callbacks.py", line 51, in read_response
    links = self.parse_links()
  File "loop-with-callbacks.py", line 67, in parse_links
    raise Exception('parse error')
Exception: parse error

```
异常堆栈中只显示事件循环在执行回调。我们无法知道什么导致了错误。这条链的两端都被破坏：我们忘记了要去哪里，也不知道从哪里来。这种丢失上下文称为“堆栈撕裂”，经常迷惑开发者。堆栈撕裂也阻止我们为回调链设置异常处理，也就是“try/except”块包裹的函数调用及其调用树。

所以，我们避免讨论多线程和异步的效率，有关于哪个更易发错误的争论：多线程下，如果同步使用错误，容易受到数据竞争的影响。然而，回调因为堆栈撕裂的存在而难以调试。
