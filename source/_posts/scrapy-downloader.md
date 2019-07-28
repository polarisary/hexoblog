---
title: Scrapy下载流程解析
date: 2018-06-25 21:40:57
categories: 源码研究 #文章文类
tags: [Scrapy,源码,python] #文章标签，多于一项时用这种格式
---
对照下面的脑图，理解整个Scrapy下载流程：
![Scrapy下载流程](scrapy_downloader.jpg)

首先接着上篇，Engine中注册到事件循环的_next_request_from_scheduler()方法开始。

> 实际上注册的是_next_request()，但_next_request()中真正执行的是_next_request_from_scheduler()

看下这个方法：

```
def _next_request_from_scheduler(self, spider):
    slot = self.slot
    request = slot.scheduler.next_request()
    if not request:
        return
    d = self._download(request, spider)
    d.addBoth(self._handle_downloader_output, request, spider)
    d.addErrback(lambda f: logger.info('Error while handling downloader output',
                                       exc_info=failure_to_exc_info(f),
                                       extra={'spider': spider}))
    d.addBoth(lambda _: slot.remove_request(request))
    d.addErrback(lambda f: logger.info('Error while removing request from slot',
                                       exc_info=failure_to_exc_info(f),
                                       extra={'spider': spider}))
    d.addBoth(lambda _: slot.nextcall.schedule())
    d.addErrback(lambda f: logger.info('Error while scheduling new request',
                                       exc_info=failure_to_exc_info(f),
                                       extra={'spider': spider}))
    return d

def _download(self, request, spider):
    slot = self.slot
    slot.add_request(request)
    def _on_success(response):
        assert isinstance(response, (Response, Request))
        if isinstance(response, Response):
            response.request = request # tie request to response received
            logkws = self.logformatter.crawled(request, response, spider)
            logger.log(*logformatter_adapter(logkws), extra={'spider': spider})
            self.signals.send_catch_log(signal=signals.response_received, \
                response=response, request=request, spider=spider)
        return response

    def _on_complete(_):
        slot.nextcall.schedule()
        return _

    dwld = self.downloader.fetch(request, spider)
    dwld.addCallbacks(_on_success)
    dwld.addBoth(_on_complete)
    return dwld
```

结合上面我总结的脑图，实际上是调用Downloader的fetch()方法:
```
def fetch(self, request, spider):
    def _deactivate(response):
        self.active.remove(request)
        return response

    self.active.add(request)
    dfd = self.middleware.download(self._enqueue_request, request, spider)
    return dfd.addBoth(_deactivate)

```
这个fetch方法有会调用middleware的download方法；这里的middleware是DownloaderMiddlewareManager，会实例化配置的所有下载中间件。并在download()方法中依序执行process_request、process_response方法，其中process_request是正序执行、process_response是逆序执行。并且会在所有中间件执行process_request之后，process_response执行之前执行真正的下载方法，这个方法是Downloader调用middleware时注册进来的_enqueue_request方法；看下面这个方法：
```
def _enqueue_request(self, request, spider):
    key, slot = self._get_slot(request, spider)
    request.meta['download_slot'] = key

    def _deactivate(response):
        slot.active.remove(request)
        return response

    slot.active.add(request)
    deferred = defer.Deferred().addBoth(_deactivate)
    slot.queue.append((request, deferred))
    self._process_queue(spider, slot)
    return deferred

def _process_queue(self, spider, slot):
    if slot.latercall and slot.latercall.active():
        return

    # Delay queue processing if a download_delay is configured
    now = time()
    delay = slot.download_delay()
    if delay:
        penalty = delay - now + slot.lastseen
        if penalty > 0:
            slot.latercall = reactor.callLater(penalty, self._process_queue, spider, slot)
            return

    # Process enqueued requests if there are free slots to transfer for this slot
    while slot.queue and slot.free_transfer_slots() > 0:
        slot.lastseen = now
        request, deferred = slot.queue.popleft()
        dfd = self._download(slot, request, spider)
        dfd.chainDeferred(deferred)
        # prevent burst if inter-request delays were configured
        if delay:
            self._process_queue(spider, slot)
            break
```

看这里会做相应的并发控制，最终会调用_download()方法；
```
def _download(self, slot, request, spider):
    # The order is very important for the following deferreds. Do not change!

    # 1. Create the download deferred
    dfd = mustbe_deferred(self.handlers.download_request, request, spider)

    # 2. Notify response_downloaded listeners about the recent download
    # before querying queue for next request
    def _downloaded(response):
        self.signals.send_catch_log(signal=signals.response_downloaded,
                                    response=response,
                                    request=request,
                                    spider=spider)
        return response
    dfd.addCallback(_downloaded)

    # 3. After response arrives,  remove the request from transferring
    # state to free up the transferring slot so it can be used by the
    # following requests (perhaps those which came from the downloader
    # middleware itself)
    slot.transferring.add(request)

    def finish_transferring(_):
        slot.transferring.remove(request)
        self._process_queue(spider, slot)
        return _

    return dfd.addBoth(finish_transferring)
```

这里会调用handles的download_request()方法；handlers是DownloadHandlers，会加载配置中所有的DOWNLOAD_HANDLERS并实例化。

```
def download_request(self, request, spider):
    scheme = urlparse_cached(request).scheme
    handler = self._get_handler(scheme)
    if not handler:
        raise NotSupported("Unsupported URL scheme '%s': %s" %
                           (scheme, self._notconfigured[scheme]))
    return handler.download_request(request, spider)
```

这个地方会根据Request的协议类型，调用相应的handler执行下载请求；下面以Http为例，继续下面的流程；
> HttpDownloadHandler其实是HTTP10DownloadHandler的扩展，实际的下载器是HTTP10DownloadHandler

```
def download_request(self, request, spider):
    """Return a deferred for the HTTP download"""
    factory = self.HTTPClientFactory(request)
    self._connect(factory)
    return factory.deferred

def _connect(self, factory):
    host, port = to_unicode(factory.host), factory.port
    if factory.scheme == b'https':
        return reactor.connectSSL(host, port, factory,
                                  self.ClientContextFactory())
    else:
        return reactor.connectTCP(host, port, factory)
```

这里直接调用的Twisted的相关网络实现来完成下载请求的。