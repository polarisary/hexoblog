---
title: Canal系列01-整体介绍
date: 2019-05-16 18:29:58
categories: Canal系列
tags: [canal]
---

## 一、项目定位及应用场景
Canal是使用java开发的基于数据库增量日志解析，提供增量数据订阅&消费，目前主要支持mysql。目前我们主要使用Canal接收MySQL的binlog，从而构建数据库中数据的变更历史，供业务方使用。

## 二、工作原理
![Canal原理图](canal原理.jpeg)
- 1）canal模拟mysql slave的交互协议，伪装自己为mysql slave，向mysql master发送dump协议
- 2）mysql master收到dump请求，开始推送binary log给slave(也就是canal)
- 3）canal解析binary log对象(原始为byte流)

## 三、架构
![canal架构图](canal架构.png)
其中server代表一个canal运行实例，对应于一个jvm，instance对应于一个数据通道 （1个server对应1..n个instance)
instance模块：
- eventParser (数据源接入，模拟slave协议和master进行交互，协议解析)
- eventSink (Parser和Store链接器，进行数据过滤，加工，分发的工作)
- eventStore (数据存储)
- metaManager (增量订阅&消费信息管理器)

## 四、源码结构
![canal源码](canal02.png)
Canal的源代码如架构图中所示，分为server、parse、sink、store、meta、protocol等
- server主要提供Http服务，client通过Http与server交互
- instance代表一个数据通道，包括：
    - parse模块，主要负责解析master推送的binlog
    - sink模块，对解析后的binlog进行过滤，路由分发、归并、加工等
    - store模块，主要为sink加工后的数据提供存储
    - meta模块，提供instance级别的消费位点持久化

protocol模块，提供数据库相关协议支持，目前主要是MySQL
prometheus模块，主要提供对Canal的监控
deployer模块是Canal的主模块，提供打包部署，启动等等