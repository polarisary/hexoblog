---
title: MySQL-索引概述
date: 2018-10-25 11:40:33
categories: MySQL
tags: [MySQL,聚集索引,辅助索引]
---
## 前言
索引是应用程序开发和设计的一个重要的方面。若索引太多，会影响应用程序的性能；若没有索引，对查询性能又有影响。所以，需要找到一个平衡点，这对应用程序设计、开发至关重要。

## InnoDB索引概述
### 常见的索引分类
- B+Tree索引
- 全文索引
- 哈希索引
> InnoDB存储引擎支持的哈希索引是自适应的，InnoDB会根据表的使用情况，自动生成Hash索引，不能认为干预。

## B+Tree索引
B+Tree索引是传统意义上的索引结构，是目前关系型数据库使用的最为常用和有效的索引类型。
> B+Tree中的B不是二叉（binary），而是代表平衡（balance），因为B+Tree是从平衡二叉树演化过来的，但不是二叉树。

B+Tree索引并不能找到给定键的具体行，只能找到查找数据行所在的页，然后再通过将页读入内存，在内存中查找，最后得到查找的数据。

数据中B+Tree索引分为聚集索引和辅助索引，不管是聚集还是辅助索引，内部都是基于B+Tree的，即高度平衡的，叶子节点存放所有数据。聚集索引和辅助索引的主要区别是叶子节点是否存放一整行数据。

### 聚集索引
聚集索引就是按表的主键构造一颗B+Tree，叶子节点存放表的行数据。所以，叶子节点也称为数据页。同时每个数据页通过双向链表连接。

聚集索引的存储并不是物理上连续的，而是逻辑上连续的。
- 一是因为页是通过双向链表链接的，数据页是按主键顺序排序。
- 二是因为每个数据页中的记录行也是通过双向链表维护的，物理上也可以不按主键顺序存储。

InnoDB引擎的表数据是通过主键索引结构来组织的，叶子节点存放行数据，是一种B+Tree文件组织。

可以快速通过主键定位数据，在创建表时，无论是否有明确的主键，InnoDB都会为表自动创建一个主键索引。

实际使用过程中，当通过主键来查询某些数据时，先通过B+Tree快速定位到叶子节点地址；由于叶子节点是磁盘块（4k）大小的整数倍（4x4=16k，InnoDB的页大小为16k），这样通过连续地址快速I/O将整个页内容加载到内存中，然后在内存中筛选出目标数据。

由于InnoDB的主键索引的存储是按主键的顺序存储的，所以InnoDB的主键索引是聚集索引，并且每张表只允许一个聚集索引；

### 辅助索引

辅助索引的叶子节点并不包含行记录的全部数据，二是包含一个书签，书签就是相应行数据的聚集索引键。因此，还需要通过聚集索引来获取行的全部数据。

除了主键索引以外的索引都称为InnoDB的辅助索引，也称为二级索引。

辅助索引的存储结构也是B+Tree，和主索引不同的是，叶子节点存储的不是行数据，而是主键值，所以，通过辅助索引定位到目标数据后（其实是目标数据的id），还需要通过主键，再通过主索引得到真正的目标数据；

### 哈希索引
时间复杂度O（1），不只是存在于索引中，几乎每个应用程序都应用到这个数据结构。

InnoDB存储引擎使用哈希算法来对字典进行查找，使用链表方式解决哈希ch

## 全文检索

全文检索使用倒排索引来实现