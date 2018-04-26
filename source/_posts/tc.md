---
layout: linux
title: Linux TC限流
date: 2018-03-27 21:52:15
categories: Linux
tags: [Linux,TC,QOS]
---
流量控制的一个基本概念是队列(Qdisc)，每个网卡都与一个队列(Qdisc)相联系， 每当内核需要将报文分组从网卡发送出去， 都会首先将该报文分组添加到该网卡所配置的队列中， 由该队列决定报文分组的发送顺序。因此可以说，所有的流量控制都发生在队列中.

在Linux中，流量控制都是通过TC这个工具来完成的。通常， 要对网卡进行流量控制的配置，需要进行如下的步骤:
- 为网卡配置一个队列;
- 在该队列上建立分类;
- 根据需要建立子队列和子分类;
- 为每个分类建立过滤器。

Linux TC中的队列有CBQ、HTB等，CBQ 比较复杂，不容易理解。HTB(HierarchicaIToken Bucket)是一个可分类的队列， 与其他复杂的队列类型相比，HTB具有功能强大、配置简单及容易上手等优点。

### 一、创建队列
```
tc qdisc add dev eth0 root handle 1: htb default 11

”dev eth0 表示要操作的网卡为eth0。
”root 表示为网卡eth0添加的是一个根队列。
”handle 1: 表示队列的句柄为1:。
”htb 表示要添加的队列为HTB队列。
”default 11 是htb特有的队列参数，意思是所有未分类的流量都将分配给类别1:11。
```
### 二、创建分类
```
tc class add dev eth0 parent 1: classid 1:1 htb rate 40mbit ceil 40mbit
tc class add dev eth0 parent 1: classid 1:12 htb rate 10mbit ceil 10mbit

”parent 1:”表示类别的父亲为根队列1:。
”classid1:11″表示创建一个标识为1:11的类别，
”rate 40mbit”表示系统将为该类别确保带宽40mbit，
”ceil 40mbit”，表示该类别的最高可占用带宽为40mbit。
”burst 40mbit”，表示该类别的峰值可占用带宽为40mbit。
```
### 三、设置过滤器
```
tc filter add dev eth0 protocol ip parent 1:0 prio 1 u32 match ip dport 80 0xffff flowid 1:11
tc filter add dev eth0 prtocol ip parent 1:0 prio 1 u32 match ip dport 25 0xffff flowid 1:12

”protocol ip”表示该过滤器应该检查报文分组的协议字段。
”prio 1″ 表示它们对报文处理的优先级是相同的，对于不同优先级的过滤器， 系统将按照从小到大的优先级。顺序来执行过滤器， 对于相同的优先级，系统将按照命令的先后顺序执行。这几个过滤器还用到了u32选择器(命令中u32后面的部分)来匹配不同的数据流。以第一个命令为例，判断的是dport字段，如果该字段与Oxffff进行与操作的结果是80
”flowid 1:11″ 表示将把该数据流分配给类别1:1 1。
```
### 四、配合iptables
TC作用:建立数据通道, 建立的通道有数据包管理方式, 通道的优先级, 通道的速率(这就是限速)
iptables作用：决定哪个ip 或者 mac 或者某个应用, 走哪个通道.

### 五、示例
限制网卡eth0 10Mbps
```
tc qdisc add dev eth0 root tbf rate 10mbit burst 10kb lat 400.0ms
tc -s qdisc ls dev eth0
```

六、参考
[Linux tc QOS 详解][1]
[Linux 流量控制实施指南][2]

[1]: http://www.wy182000.com/2013/04/15/linux-tc-%E8%AF%A6%E8%A7%A3/        "Linux tc QOS 详解" 
[2]: http://www.wy182000.com/2013/04/17/linux-%E6%B5%81%E9%87%8F%E6%8E%A7%E5%88%B6%E5%AE%9E%E6%96%BD%E6%8C%87%E5%8D%97/	"Linux 流量控制实施指南" 
