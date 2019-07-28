---
title: 【Dubbo系列01】了解RPC
date: 2019-07-28 21:49:34
categories: Dubbo系列
tags: [Dubbo]
---

7月底，自从上个月使用和研究Canal相关技术原理，这个月都在利用工作之余研究Dubbo相关技术，但一直没有写Dubbo相关博客，是因为Dubbo涉及的技术点比较多，自己对Dubbo没有一个整体的脉络，感觉不知道从哪里开始动笔。

月初的时候慢慢开始研究服务治理相关的技术，于是开始了Dubbo学习，其实，在刚毕业那会已经对Dubbo有所了解，只是停留在使用层面。加上中间在创业公司使用Python技术栈，所以一直没有深入学习，这次开始决定深入学习下Dubbo及微服务领域的技术。

经过大概一个月的时间，基本了解了Dubbo涉及的各个技术点，月末也对一月的学习做个总结，也为下个月的学习开个头。对Dubbo有个了大概的轮廓，在接下来一个月准备对Dubbo相关技术点及原理分别深入学习研究。

## 一、定义
RPC是指远程过程调用，它跟方法调用的区别在于是否是在同一个JVM下。

## 二、面临的问题
既然RPC调用不是在同一个JVM里面，那就面临着下面几个问题：
- 通讯问题
客户端和服务端需要通过网络（TCP）进行通讯，使用长链接或者短连接等。
- 寻址问题
客户端和服务端需要通过某种协议，约定好客户端通过RPC可以正确的调用到服务端的相应方法。
- 网络传输问题
客户端和服务端需要解决参数和返回结果如何在网络上传输的问题，也就是序列化和反序列化。

## 三、RPC框架
- Apache Dubbo
阿里巴巴开源的一个Java高性能优秀的服务框架，使得应用可通过高性能的 RPC 实现服务的输出和输入功能，可以和 Spring框架无缝集成。
- Motan
新浪微博开源的一个Java 框架。
- rpcx
Go语言生态圈的Dubbo， 比Dubbo更轻量，实现了Dubbo的许多特性，借助于Go语言优秀的并发特性和简洁语法，可以使用较少的代码实现分布式的RPC服务。
- grpc
Google开发的高性能、通用的开源RPC框架，其由Google主要面向移动应用开发并基于HTTP/2协议标准而设计，基于ProtoBuf(Protocol Buffers)序列化协议开发，且支持众多开发语言。
- thrift
Apache的一个跨语言的高性能的服务框架。

## 四、Dubbo架构

![Dubbo架构图](architecture.png)

从架构图可以了解到，Dubbo主要包括5个角色：
- Provider
服务提供者，暴露服务。
- Consumer
服务消费者，调用远程服务。
- Registry
注册中心，服务注册、发现中心。
- Container
服务运行容器
- Monitor
服务监控中心，服务消费者& 服务提供者需要定时向Monitor汇报调用次数、调用时间等。

#### 具体流程：
0：Container负责启动，加载，运行服务提供者
1：Provider启动时，向Registry注册自己提供的服务
2：Consumer启动时，向Registry订阅自己关注的服务
3：Registry返回给Consumer关注的Provider地址，如果有变更，Registry基于长链接推送变更数据给Consumer
4：Consumer从Provider地址列表中，基于软负载均衡策略，选一台Provider进行远程调用，如果调用失败，则根据相应策略（failover、failfast等）重试其他Provider或者抛异常
5：Consumer和Provider，在内存中累计调用次数和调用时间，定时发送统计数据给Monitor