---
title: Canal系列04-并行解析Disruptor实现
date: 2019-06-19 23:03:14
categories: Canal系列
tags: [canal]
---
## 一、Disruptor介绍
Disruptor它是一个开源的并发框架，并获得2011 Duke’s 程序框架创新奖，能够在无锁的情况下实现网络的Queue并发操作。

研发的初衷是解决内存队列的延迟问题（在性能测试中发现竟然与I/O操作处于同样的数量级）。基于Disruptor开发的系统单线程能支撑每秒600万订单，2010年在QCon演讲后，获得了业界关注。

目前，包括Apache Storm、Camel、Log4j 2在内的很多知名项目都应用了Disruptor以获取高性能。在美团技术团队它也有不少应用，有的项目架构借鉴了它的设计机制。

Canal在并行解析binlog的实现中使用了Disruptor，所有这里需要对Disruptor有一定的了解，更多的使用方法及原理请查阅文章下面的参考文献

## 二、并行解析实现
接上篇[Canal系列03-Parser模块](http://blog.7street.top/2019/06/17/canal03/)说到并行解析是Disruptor实现。下面的注释代码方便理解，需要对Disruptor有一定的了解才能理解哦。这也给我们提供了一个使用多阶段多线程使用Disruptor的最佳实践。
```
public void start() {
        // 设置running状态字段
        super.start();
        this.exception = null;
        // 初始化RingBuffer，简单解析，事件深度解析，sink store多线程协作
        this.disruptorMsgBuffer = RingBuffer.createSingleProducer(new MessageEventFactory(),
            ringBufferSize,
            new BlockingWaitStrategy());
        int tc = parserThreadCount > 0 ? parserThreadCount : 1;
        this.parserExecutor = Executors.newFixedThreadPool(tc, new NamedThreadFactory("MultiStageCoprocessor-Parser-" + destination));

        this.stageExecutor = Executors.newFixedThreadPool(2, new NamedThreadFactory("MultiStageCoprocessor-other-" + destination));
        
        // barrier用来维护事件处理顺序的
        SequenceBarrier sequenceBarrier = disruptorMsgBuffer.newBarrier();
        ExceptionHandler exceptionHandler = new SimpleFatalExceptionHandler();
        // stage 2 -> 简单解析，事件类型、DDL解析构造TableMeta、维护位点信息、是否需要DML解析
        this.logContext = new LogContext();
        simpleParserStage = new BatchEventProcessor<MessageEvent>(disruptorMsgBuffer,
            sequenceBarrier,
            new SimpleParserStage(logContext));
        simpleParserStage.setExceptionHandler(exceptionHandler);
        disruptorMsgBuffer.addGatingSequences(simpleParserStage.getSequence());

        // stage 3 -> 事件深度解析 (多线程, DML事件数据的完整解析)
        SequenceBarrier dmlParserSequenceBarrier = disruptorMsgBuffer.newBarrier(simpleParserStage.getSequence());
        WorkHandler<MessageEvent>[] workHandlers = new DmlParserStage[tc];
        for (int i = 0; i < tc; i++) {
            // 事件解析 eventhandler
            workHandlers[i] = new DmlParserStage();
        }
        // 使用workerPool管理多个解析线程
        workerPool = new WorkerPool<MessageEvent>(disruptorMsgBuffer,
            dmlParserSequenceBarrier,
            exceptionHandler,
            workHandlers);
        Sequence[] sequence = workerPool.getWorkerSequences();
        disruptorMsgBuffer.addGatingSequences(sequence);

        // stage 4 -> 最后投递到store (单线程)
        SequenceBarrier sinkSequenceBarrier = disruptorMsgBuffer.newBarrier(sequence);
        sinkStoreStage = new BatchEventProcessor<MessageEvent>(disruptorMsgBuffer,
            sinkSequenceBarrier,
            new SinkStoreStage());// 将解析后的event存储到transactionBuffer中
        sinkStoreStage.setExceptionHandler(exceptionHandler);
        disruptorMsgBuffer.addGatingSequences(sinkStoreStage.getSequence());

        // start work，启动各个阶段的处理线程
        stageExecutor.submit(simpleParserStage);
        stageExecutor.submit(sinkStoreStage);
        workerPool.start(parserExecutor);
    }
```
## 三、参考文献
[高性能队列—Disruptor](https://tech.meituan.com/2016/11/18/disruptor.html)
[并发框架DISRUPTOR译文](https://coolshell.cn/articles/9169.html)