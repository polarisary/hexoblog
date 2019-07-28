---
title: Memcache内部原理
date: 2018-08-30 22:38:46
categories: 开源项目
tags: [memcache,内存]
---
### 基本数据结构
![memcache](memcache.jpg)
- chunk
> 是一系列固定大小的内存空间，用于缓存数据的内存块。
- slab
> 用于切分为chunk的内存块，一个slabclass可挂载多个slabs
- slabclass
> 用于管理相同chunk大小的内存结构
- item
> 用于管理key/value的数据结构，一个item放于一个chunk中
- LRU list
> 用于管理各个slabclass的最近访问过的item, 以用于item踢出时的选择，list头部是最近访问过的item
- hashtable
> 用于查找数据时item寻址，对key计算hash值，再在hashtable中找到对应的item, 取出数据
- slots list
> 是slabclass用于管理当前class的空闲item的list, 由slabclass结构中的slots指针指向
- Page
> 内存分配的最小单位，默认1M，可以通过-I参数在启动时指定。如果需要申请内存时，memcached会划分出一个新的page并分配给需要的slab区域。

### 常规的内存使用方式
- 预分配
> 可能浪费内存，是一种拿空间换时间的方式，提高速度
- 动态分配
> 相对来说比预分配慢点，但节约内存

### memcache内存分配
为了规避内存碎片问题，memcache使用的是Slab Allocation的预分配的方式使用内存。

内存分配策略：按slab需求分配page，各slab按需使用chunk存储。

> Slab Allocation是将内存按指定大小分块（chunk），将相同大小的块组成分组。默认chunk是1.25倍增加的，并且分配的内存不会释放，可以重复使用，避免内存碎片的产生。
> 
> Memcached 在启动时通过-m参数指定最大使用内存，但memcache并不会一启动就占用这么大内存，而是根据需要逐步分配给各个slab的。
> 
> 如果一个新的数据需要缓存时，memcached先根据数据大小选择一个合适的slab，再查看该slab是否还有空闲的chunk，有则直接存进去，否则需要slab申请一个page的内存，并切分成多个chunk，将数据存到切分出的第一个chunk中。
>
> 如果没有可用的内存分配给slab，系统就会触发LRU机制，通过删除冷数据来释放内存空间。
> 
> PS：服务端维护着一个未使用的内存块的列表，所以很容易就知道slab下是否有空闲的chunk

### 惰性过期机制
memcache内部没有提供过期检查机制，而是在get时依据记录的过期时间检查是否过期。
默认，内部也维护一套LRU置换算法，当设定的内存满了的时候，会按照置换算法删除一些冷数据，LRU不是全局的，而是对slab而言的。

### 分布式策略
- 余数算法
> 先key的整数散列值，再除以服务器数量，根据得到的余数确定存储的服务器。
> 
> 优点：简单、高效；
> 
> 缺点：当服务器增加或者减少时，几乎所有的缓存都会失效。
- 散列算法（一致性hash）
> - 先算出所有服务器散列值，将其分布到0~2^32的圆上
> - 同样的方法，计算出key的散列值，并分布到上面的圆上
> - 从key映射的位置，顺时针查找，将数据存储到查找到的第一台服务器上，大于2^32还没有找到，就存储到第一台服务器上。
>
> 优点：当增加或减少服务器时，只影响增加或者减少服务器的圆上位置的顺时针下一台服务器上的数据

memcache使用客户端一致性hash算法实现分布式存储。

### 特性
- memcache保存的item的数量在内存足够的情况下是没有限制的
- key的最大长度：250字节
- value的最大长度：1m字节
- memcache服务端是不安全的，可以通过Telnet，flush_all将所有数据失效
- 不能遍历所有item，很慢并且阻塞其他操作

### 参考
[深入memcached内部](http://lostphp.com/blog/564.html)