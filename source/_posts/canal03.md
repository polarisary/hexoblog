---
title: Canal系列03-Parser模块
date: 2019-06-17 23:31:29
categories: Canal系列
tags: [canal]
---
## 一、入口
接上节，从Spring配置文件file-instance.xml中可以看到，eventParser继承了base-instance.xml中的baseEventParser，查看base-instance.xml可以看到，eventParser是com.alibaba.otter.canal.parse.inbound.mysql.rds.RdsBinlogEventParserProxy的实例，就是调用的RdsBinlogEventParserProxy的start()方法。

```
# file-instance.xml
<bean id="eventParser" parent="baseEventParser">

# base-instance.xml
<bean id="baseEventParser" class="com.alibaba.otter.canal.parse.inbound.mysql.rds.RdsBinlogEventParserProxy" abstract="true">
   <property name="accesskey" value="${canal.aliyun.accesskey:}" />
   <property name="secretkey" value="${canal.aliyun.secretkey:}" />
   <property name="instanceId" value="${canal.instance.rds.instanceId:}" />
</bean>
```

## 二、代码解析
RdsBinlogEventParserProxy.start()方法一路super.start()，最终调用的是父类AbstractEventParser的start()方法。
```
// eventParser start一路super最终调用的是AbstractEventParser的start()方法
public void start() {
    // 设置running为true
    super.start();
    MDC.put("destination", destination);
    // 配置transaction buffer
    // 初始化缓冲队列
    transactionBuffer.setBufferSize(transactionSize);// 设置buffer大小
    transactionBuffer.start();
    // 构造bin log parser
    binlogParser = buildParser();// 初始化一下BinLogParser
    binlogParser.start();
    // 启动工作线程
    parseThread = new Thread(new Runnable() {

        public void run() {
            MDC.put("destination", String.valueOf(destination));
            ErosaConnection erosaConnection = null;
            while (running) {
                try {
                    // 开始执行replication
                    // 1. 构造Erosa连接
                    erosaConnection = buildErosaConnection();

                    // 2. 启动一个心跳线程
                    startHeartBeat(erosaConnection);

                    // 3. 执行dump前的准备工作
                    preDump(erosaConnection);

                    erosaConnection.connect();// 链接

                    long queryServerId = erosaConnection.queryServerId();
                    if (queryServerId != 0) {
                        serverId = queryServerId;
                    }
                    // 4. 获取最后的位置信息
                    long start = System.currentTimeMillis();
                    logger.warn("---> begin to find start position, it will be long time for reset or first position");
                    EntryPosition position = findStartPosition(erosaConnection);
                    final EntryPosition startPosition = position;
                    if (startPosition == null) {
                        throw new PositionNotFoundException("can't find start position for " + destination);
                    }

                    if (!processTableMeta(startPosition)) {
                        throw new CanalParseException("can't find init table meta for " + destination
                                                      + " with position : " + startPosition);
                    }
                    long end = System.currentTimeMillis();
                    logger.warn("---> find start position successfully, {}", startPosition.toString() + " cost : "
                                                                             + (end - start)
                                                                             + "ms , the next step is binlog dump");
                    // 重新链接，因为在找position过程中可能有状态，需要断开后重建
                    erosaConnection.reconnect();
                    // 非并行模式下，接到master的event交给sinkHandler处理
                    final SinkFunction sinkHandler = new SinkFunction<EVENT>() {

                        private LogPosition lastPosition;

                        public boolean sink(EVENT event) {
                            try {
                                // 这里会调用binlogParser进行解析成CanalEntry.Entry
                                CanalEntry.Entry entry = parseAndProfilingIfNecessary(event, false);

                                if (!running) {
                                    return false;
                                }

                                if (entry != null) {
                                    exception = null; // 有正常数据流过，清空exception
                                    // 将数据存入内存队列中
                                    transactionBuffer.add(entry);
                                    // 记录一下对应的positions
                                    this.lastPosition = buildLastPosition(entry);
                                    // 记录一下最后一次有数据的时间
                                    lastEntryTime = System.currentTimeMillis();
                                }
                                return running;
                            } catch (TableIdNotFoundException e) {
                                throw e;
                            } catch (Throwable e) {
                                if (e.getCause() instanceof TableIdNotFoundException) {
                                    throw (TableIdNotFoundException) e.getCause();
                                }
                                // 记录一下，出错的位点信息
                                processSinkError(e,
                                    this.lastPosition,
                                    startPosition.getJournalName(),
                                    startPosition.getPosition());
                                throw new CanalParseException(e); // 继续抛出异常，让上层统一感知
                            }
                        }

                    };

                    // 4. 开始dump数据，默认并行，使用disruptor.RingBuffer实现
                    if (parallel) {
                        // build stage processor
                        multiStageCoprocessor = buildMultiStageCoprocessor();
                        if (isGTIDMode() && StringUtils.isNotEmpty(startPosition.getGtid())) {
                            // 判断所属instance是否启用GTID模式，是的话调用ErosaConnection中GTID对应方法dump数据
                            GTIDSet gtidSet = MysqlGTIDSet.parse(startPosition.getGtid());
                            ((MysqlMultiStageCoprocessor) multiStageCoprocessor).setGtidSet(gtidSet);
                            multiStageCoprocessor.start();
                            erosaConnection.dump(gtidSet, multiStageCoprocessor);
                        } else {
                            multiStageCoprocessor.start();
                            if (StringUtils.isEmpty(startPosition.getJournalName())
                                && startPosition.getTimestamp() != null) {
                                erosaConnection.dump(startPosition.getTimestamp(), multiStageCoprocessor);
                            } else {
                                erosaConnection.dump(startPosition.getJournalName(),
                                    startPosition.getPosition(),
                                    multiStageCoprocessor);
                            }
                        }
                    } else {
                        if (isGTIDMode() && StringUtils.isNotEmpty(startPosition.getGtid())) {
                            // 判断所属instance是否启用GTID模式，是的话调用ErosaConnection中GTID对应方法dump数据
                            // 这里会不断的向master fetch binlog直到running为false
                            erosaConnection.dump(MysqlGTIDSet.parse(startPosition.getGtid()), sinkHandler);
                        } else {
                            if (StringUtils.isEmpty(startPosition.getJournalName())
                                && startPosition.getTimestamp() != null) {
                                erosaConnection.dump(startPosition.getTimestamp(), sinkHandler);
                            } else {
                                erosaConnection.dump(startPosition.getJournalName(),
                                    startPosition.getPosition(),
                                    sinkHandler);
                            }
                        }
                    }
                } catch (TableIdNotFoundException e) {
                    exception = e;
                    // 特殊处理TableIdNotFound异常,出现这样的异常，一种可能就是起始的position是一个事务当中，导致tablemap
                    // Event时间没解析过
                    needTransactionPosition.compareAndSet(false, true);
                    logger.error(String.format("dump address %s has an error, retrying. caused by ",
                        runningInfo.getAddress().toString()), e);
                } catch (Throwable e) {
                    processDumpError(e);
                    exception = e;
                    if (!running) {
                        if (!(e instanceof java.nio.channels.ClosedByInterruptException || e.getCause() instanceof java.nio.channels.ClosedByInterruptException)) {
                            throw new CanalParseException(String.format("dump address %s has an error, retrying. ",
                                runningInfo.getAddress().toString()), e);
                        }
                    } else {
                        logger.error(String.format("dump address %s has an error, retrying. caused by ",
                            runningInfo.getAddress().toString()), e);
                        sendAlarm(destination, ExceptionUtils.getFullStackTrace(e));
                    }
                    if (parserExceptionHandler != null) {
                        parserExceptionHandler.handle(e);
                    }
                } finally {
                    // 重新置为中断状态
                    Thread.interrupted();
                    // 关闭一下链接
                    afterDump(erosaConnection);
                    try {
                        if (erosaConnection != null) {
                            erosaConnection.disconnect();
                        }
                    } catch (IOException e1) {
                        if (!running) {
                            throw new CanalParseException(String.format("disconnect address %s has an error, retrying. ",
                                runningInfo.getAddress().toString()),
                                e1);
                        } else {
                            logger.error("disconnect address {} has an error, retrying., caused by ",
                                runningInfo.getAddress().toString(),
                                e1);
                        }
                    }
                }
                // 出异常了，退出sink消费，释放一下状态
                eventSink.interrupt();
                transactionBuffer.reset();// 重置一下缓冲队列，重新记录数据
                binlogParser.reset();// 重新置位
                if (multiStageCoprocessor != null && multiStageCoprocessor.isStart()) {
                    // 处理 RejectedExecutionException
                    try {
                        multiStageCoprocessor.stop();
                    } catch (Throwable t) {
                        logger.debug("multi processor rejected:", t);
                    }
                }

                if (running) {
                    // sleep一段时间再进行重试
                    try {
                        Thread.sleep(10000 + RandomUtils.nextInt(10000));
                    } catch (InterruptedException e) {
                    }
                }
            }
            MDC.remove("destination");
        }
    });

    parseThread.setUncaughtExceptionHandler(handler);
    parseThread.setName(String.format("destination = %s , address = %s , EventParser",
        destination,
        runningInfo == null ? null : runningInfo.getAddress()));
    parseThread.start();
}
```

里面基本上都添加了注释，解析部分分两张情况，第一种是非并行模式下，使用sinkHandler解析并存储解析后的数据到缓冲队列中。第二种是并行情况下，使用Disruptor实现

## 三、总结
![Canal Parser设计](eventParser.jpeg)
如上面设计图中所示，eventParser作为一个线程被启动，内部将自己伪装成mysql slave，与master通讯，fetch binlog，在通过binlog parser解析，最终sink到缓冲队列。并行模式下通过Disruptor实现并行解析的，下一部分重点看下Disruptor并行解析的实现。