---
title: Canal系列02-Deployer模块
date: 2019-06-16 22:10:32
categories: Canal系列
tags: [canal]
---
## 一、简介
通过deployer模块，我们可以直接使用maven打出一个Canal可执行包，项目结构包括：

- bin项目启动/停止/初始化脚本
- conf项目配置文件
- lib项目依赖jar
- logs项目执行的日志目录

## 二、源码分析
![Canal](canal 02.png)
- 1）Canal启动的类是CanalLauncher，通过解析配置文件，调用CanalStater.start(properties)，这里CanalStater->CanalStarter，感觉可能是类名弄错了，这个类不复杂。
- 2）CanalStater首先会判断是否是使用MQ来接收binlog的，Canal支持将binlog直接发送的kafka或者RocketMQ中。然后启动CanalController这个类的start方法。
- 3）CanalController这个是比较复杂的类，里面包括Canal实例及嵌入式服务的启动，我在代码里加了注释方便理解。

```
// 构造方法很长
public CanalController(final Properties properties){
    managerClients = MigrateMap.makeComputingMap(new Function<String, CanalConfigClient>() {

        public CanalConfigClient apply(String managerAddress) {
            return getManagerClient(managerAddress);
        }
    });

    // 初始化全局参数设置，重要：instanceGenerator声明CanalInstanceGenerator如何生成
    // Spring模式下，通过配置default-instance.xml,实现CanalInstanceWithSpring的组装
    globalInstanceConfig = initGlobalConfig(properties);
    instanceConfigs = new MapMaker().makeMap();
    // 初始化instance config,将配置初始化到instanceConfigs中
    initInstanceConfig(properties);

    // init socketChannel
    String socketChannel = getProperty(properties, CanalConstants.CANAL_SOCKETCHANNEL);
    if (StringUtils.isNotEmpty(socketChannel)) {
        System.setProperty(CanalConstants.CANAL_SOCKETCHANNEL, socketChannel);
    }

    // 兼容1.1.0版本的ak/sk参数名
    String accesskey = getProperty(properties, "canal.instance.rds.accesskey");
    String secretkey = getProperty(properties, "canal.instance.rds.secretkey");
    if (StringUtils.isNotEmpty(accesskey)) {
        System.setProperty(CanalConstants.CANAL_ALIYUN_ACCESSKEY, accesskey);
    }
    if (StringUtils.isNotEmpty(secretkey)) {
        System.setProperty(CanalConstants.CANAL_ALIYUN_SECRETKEY, secretkey);
    }

    // 准备canal server
    cid = Long.valueOf(getProperty(properties, CanalConstants.CANAL_ID));
    ip = getProperty(properties, CanalConstants.CANAL_IP);
    port = Integer.valueOf(getProperty(properties, CanalConstants.CANAL_PORT));
    embededCanalServer = CanalServerWithEmbedded.instance();
    // 设置自定义的instanceGenerator，这里比较重要
    embededCanalServer.setCanalInstanceGenerator(instanceGenerator);
    try {
        int metricsPort = Integer.valueOf(getProperty(properties, CanalConstants.CANAL_METRICS_PULL_PORT));
        embededCanalServer.setMetricsPort(metricsPort);
    } catch (NumberFormatException e) {
        logger.info("No valid metrics server port found, use default 11112.");
        embededCanalServer.setMetricsPort(11112);
    }
    // 使用Netty创建Http Server，用来接收Canal 客户端的请求
    String canalWithoutNetty = getProperty(properties, CanalConstants.CANAL_WITHOUT_NETTY);
    if (canalWithoutNetty == null || "false".equals(canalWithoutNetty)) {
        canalServer = CanalServerWithNetty.instance();
        canalServer.setIp(ip);
        canalServer.setPort(port);
    }

    // 处理下ip为空，默认使用hostIp暴露到zk中
    if (StringUtils.isEmpty(ip)) {
        ip = AddressUtils.getHostIp();
    }
    final String zkServers = getProperty(properties, CanalConstants.CANAL_ZKSERVERS);
    if (StringUtils.isNotEmpty(zkServers)) {
        // HA 模式下初始化ZK相关节点
        zkclientx = ZkClientx.getZkClient(zkServers);
        // 初始化系统目录
        zkclientx.createPersistent(ZookeeperPathUtils.DESTINATION_ROOT_NODE, true);
        zkclientx.createPersistent(ZookeeperPathUtils.CANAL_CLUSTER_ROOT_NODE, true);
    }

    final ServerRunningData serverData = new ServerRunningData(cid, ip + ":" + port);
    ServerRunningMonitors.setServerData(serverData);
    // 通过ServerRunningMonitors注册destination实例的ServerRunningMonitor，通过ServerRunningListener启动
    // 每个destination的嵌入式服务embededCanalServer
    ServerRunningMonitors
        .setRunningMonitors(MigrateMap.makeComputingMap(new Function<String, ServerRunningMonitor>() {

            public ServerRunningMonitor apply(final String destination) {
                ServerRunningMonitor runningMonitor = new ServerRunningMonitor(serverData);
                runningMonitor.setDestination(destination);
                runningMonitor.setListener(new ServerRunningListener() {

                    public void processActiveEnter() {
                        try {
                            MDC.put(CanalConstants.MDC_DESTINATION, String.valueOf(destination));
                            embededCanalServer.start(destination);
                            if (canalMQStarter != null) {
                                canalMQStarter.startDestination(destination);
                            }
                        } finally {
                            MDC.remove(CanalConstants.MDC_DESTINATION);
                        }
                    }

                    public void processActiveExit() {
                        try {
                            MDC.put(CanalConstants.MDC_DESTINATION, String.valueOf(destination));
                            if (canalMQStarter != null) {
                                canalMQStarter.stopDestination(destination);
                            }
                            embededCanalServer.stop(destination);
                        } finally {
                            MDC.remove(CanalConstants.MDC_DESTINATION);
                        }
                    }

                    public void processStart() {
                        try {
                            if (zkclientx != null) {
                                final String path = ZookeeperPathUtils.getDestinationClusterNode(destination,
                                    ip + ":" + port);
                                initCid(path);
                                zkclientx.subscribeStateChanges(new IZkStateListener() {

                                    public void handleStateChanged(KeeperState state) throws Exception {

                                    }

                                    public void handleNewSession() throws Exception {
                                        initCid(path);
                                    }

                                    @Override
                                    public void handleSessionEstablishmentError(Throwable error) throws Exception {
                                        logger.error("failed to connect to zookeeper", error);
                                    }
                                });
                            }
                        } finally {
                            MDC.remove(CanalConstants.MDC_DESTINATION);
                        }
                    }

                    public void processStop() {
                        try {
                            MDC.put(CanalConstants.MDC_DESTINATION, String.valueOf(destination));
                            if (zkclientx != null) {
                                final String path = ZookeeperPathUtils.getDestinationClusterNode(destination,
                                    ip + ":" + port);
                                releaseCid(path);
                            }
                        } finally {
                            MDC.remove(CanalConstants.MDC_DESTINATION);
                        }
                    }

                });
                if (zkclientx != null) {
                    runningMonitor.setZkClient(zkclientx);
                }
                // 触发创建一下cid节点
                runningMonitor.init();
                return runningMonitor;
            }
        }));

    // 初始化monitor机制
    autoScan = BooleanUtils.toBoolean(getProperty(properties, CanalConstants.CANAL_AUTO_SCAN));
    if (autoScan) {
        // InstanceAction完成自动扫描配置有变更时，对实例上的嵌入式服务embededCanalServer通过ServerRunningMonitor进行重启
        defaultAction = new InstanceAction() {

            public void start(String destination) {
                InstanceConfig config = instanceConfigs.get(destination);
                if (config == null) {
                    // 重新读取一下instance config
                    config = parseInstanceConfig(properties, destination);
                    instanceConfigs.put(destination, config);
                }

                if (!embededCanalServer.isStart(destination)) {
                    // HA机制启动
                    ServerRunningMonitor runningMonitor = ServerRunningMonitors.getRunningMonitor(destination);
                    if (!config.getLazy() && !runningMonitor.isStart()) {
                        runningMonitor.start();
                    }
                }
            }

            public void stop(String destination) {
                // 此处的stop，代表强制退出，非HA机制，所以需要退出HA的monitor和配置信息
                InstanceConfig config = instanceConfigs.remove(destination);
                if (config != null) {
                    embededCanalServer.stop(destination);
                    ServerRunningMonitor runningMonitor = ServerRunningMonitors.getRunningMonitor(destination);
                    if (runningMonitor.isStart()) {
                        runningMonitor.stop();
                    }
                }
            }

            public void reload(String destination) {
                // 目前任何配置变化，直接重启，简单处理
                stop(destination);
                start(destination);
            }
        };
        // 主要是对spring模式的配置进行监控，单独启动线程每scanInterval扫描一次，
        // 通过上面的defaultAction对嵌入式的embededCanalServer进行重启
        instanceConfigMonitors = MigrateMap.makeComputingMap(new Function<InstanceMode, InstanceConfigMonitor>() {

            public InstanceConfigMonitor apply(InstanceMode mode) {
                int scanInterval = Integer
                    .valueOf(getProperty(properties, CanalConstants.CANAL_AUTO_SCAN_INTERVAL));

                if (mode.isSpring()) {
                    SpringInstanceConfigMonitor monitor = new SpringInstanceConfigMonitor();
                    monitor.setScanIntervalInSecond(scanInterval);
                    monitor.setDefaultAction(defaultAction);
                    // 设置conf目录，默认是user.dir + conf目录组成
                    String rootDir = getProperty(properties, CanalConstants.CANAL_CONF_DIR);
                    if (StringUtils.isEmpty(rootDir)) {
                        rootDir = "../conf";
                    }

                    if (StringUtils.equals("otter-canal", System.getProperty("appName"))) {
                        monitor.setRootConf(rootDir);
                    } else {
                        // eclipse debug模式
                        monitor.setRootConf("src/main/resources/");
                    }
                    return monitor;
                } else if (mode.isManager()) {
                    return new ManagerInstanceConfigMonitor();
                } else {
                    throw new UnsupportedOperationException("unknow mode :" + mode + " for monitor");
                }
            }
        });
    }
}
```

接着调用start方法：

```
public void start() throws Throwable {
    logger.info("## start the canal server[{}:{}]", ip, port);
    // 创建整个canal的工作节点
    final String path = ZookeeperPathUtils.getCanalClusterNode(ip + ":" + port);
    // ZK相关初始化
    initCid(path);
    if (zkclientx != null) {
        this.zkclientx.subscribeStateChanges(new IZkStateListener() {

            public void handleStateChanged(KeeperState state) throws Exception {

            }

            public void handleNewSession() throws Exception {
                initCid(path);
            }

            @Override
            public void handleSessionEstablishmentError(Throwable error) throws Exception {
                logger.error("failed to connect to zookeeper", error);
            }
        });
    }
    // 优先启动embeded服务，主要注册canalInstances，使用canalInstanceGenerator.generate(destination)
    embededCanalServer.start();
    // 尝试启动一下非lazy状态的通道
    for (Map.Entry<String, InstanceConfig> entry : instanceConfigs.entrySet()) {
        final String destination = entry.getKey();
        InstanceConfig config = entry.getValue();
        // 创建destination的工作节点
        if (!embededCanalServer.isStart(destination)) {
            // HA机制启动
            // 使用构造函数中注册的runningMonitor的listener启动实例上的embededCanalServer服务
            ServerRunningMonitor runningMonitor = ServerRunningMonitors.getRunningMonitor(destination);
            if (!config.getLazy() && !runningMonitor.isStart()) {
                runningMonitor.start();
            }
        }

        if (autoScan) {
            instanceConfigMonitors.get(config.getMode()).register(destination, defaultAction);
        }
    }

    if (autoScan) {
        // 自动扫描配置，启动线程扫描配置目录，有改动就重启嵌入式实例服务
        instanceConfigMonitors.get(globalInstanceConfig.getMode()).start();
        for (InstanceConfigMonitor monitor : instanceConfigMonitors.values()) {
            if (!monitor.isStart()) {
                monitor.start();
            }
        }
    }

    // 启动网络接口
    if (canalServer != null) {
        canalServer.start();
    }
}
```

## 三、嵌入式服务启动

在CanalController start中调用embededCanalServer.start(destination)启动相应destination的嵌入式服务，这里在调用相应（destination）实例的start方法启动，这个实例是如果产生的？是通过CanalController中的instanceGenerator生成的，具体有两种生成方式：
- 1）ManagerCanalInstanceGenerator()
这种方式在阿里云内部使用
- 2）SpringCanalInstanceGenerator()
这种方式社区使用较多，我们以这种方式来分析
默认使用的sprint配置文件是通过canal.properties中配置的的canal.instance.global.spring.xml = classpath:spring/file-instance.xml
也就是file-instance.xml了，查找配置中id为"instance"的bean即可。
这里是CanalInstanceWithSpring这个类，原来是调用他的start的方法，他的start的方法的实现是在父类AbstractCanalInstance中。

```
public void start() {
    super.start();
    if (!metaManager.isStart()) {
        metaManager.start();
    }

    if (!alarmHandler.isStart()) {
        alarmHandler.start();
    }

    if (!eventStore.isStart()) {
        eventStore.start();
    }

    if (!eventSink.isStart()) {
        eventSink.start();
    }

    if (!eventParser.isStart()) {
        beforeStartEventParser(eventParser);
        eventParser.start();
        afterStartEventParser(eventParser);
    }
    logger.info("start successful....");
}
```

Start方法很明确了，调用instance中meta、alarm、store、sink、parse的start方法，接下来一个个分析相应的模块。