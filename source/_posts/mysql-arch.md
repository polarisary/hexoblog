---
title: MySQL-概述
date: 2018-09-18 17:08:07
categories: MySQL
tags: [MySQL, Undo Log, Redo Log, InnoDB]
---
## 数据库与实例

- 数据库是文件集合，依照某种数据模型组织起来并存储于二级存储器中的数据集合
- 数据库实例是程序，是存在于操作系统和用户之间的数据管理软件。用户对数据库的任何操作都是在数据库实例下进行的，用户程序必须通过数据库实例和数据库交互。

## MySQL存储引擎
### InnoDB存储引擎
支持事务，主要设计目标是面向在线事务处理（OLTP）应用。行锁设计，支持外键，并支持非锁定读，支持独立的表ibd文件。从5.5.8开始成为MySQL默认的存储引擎。

InnoDB通过多版本并发控制（MVCC）来提高并发性。并实现了SQL标准的4种隔离级别，默认为RR（Repeatable Read）。

在表的数据存储上，InnoDB采用聚集索引的方式，所以每个表中的数据都是按主键顺序存放的。如果没有显示定义主键，InnoDB会为每行创建一个6字节的row_id作为主键。

### MyISAM存储引擎
不支持事务、表锁设计，支持全文索引。在MySQL 5.5.8之前是MySQL默认的存储引擎。

## InnoDB存储引擎关键特性
- 插入缓冲（Insert Buffer）
- 两次写（Double Write）
- 自适应哈希索引（Adaptive Hash Index）
- 异步IO（Async IO）
- 刷新临近页（Flush Neighbor Page）

### 插入缓冲（Insert Buffer）
1）主要功能：
    提高非唯一的辅助索引的插入性能
    
2）前提条件
- 辅助索引（或者二级索引）
- 非唯一索引

MySQL在进行插入操作时，数据页是按聚集索引（主键、主索引）顺序存放的，但对于非聚集的叶子节点（辅助索引的叶子节点存的是主键，查询时需要进行二次查找）的插入，就不是顺序的了，这时就需要离散的访问非聚集索引页，正是由于这样的随机读取的存在，导致了插入性能的下降。

为了解决辅助索引随机读取导致的性能问题，MySQL引入了Insert Buffer的设计，大概的思想是通过使用缓存，将多次对索引页的操作，合并成一次来提供性能。对非聚集索引的插入和更新操作，不会每次都直接插入到索引页中，而是先判断索引页是否在缓存池中，在，就直接插入，不在，则先放到一个Insert Buffer对象中，然后再以一定的频率和情况来对Insert Buffer和辅助索引页子节点的合并，这样，通常可以将多个插入操作合并到一个操作中，这样就大大提高了非聚集索引的插入性能。

### 两次写（Double Write）
主要功能：提高数据页的可靠性

### 自适应哈希索引（Adaptive Hash Index）

主要功能：提高索引页的检索速度

InnoDB引擎自动优化，无需人工干预

### 异步IO（Async IO）

主要功能：提高磁盘读写性能

合并IO请求，提高IOPS性能。

### 刷新临近页（Flush Neighbor Page）

主要功能：利用AIO，合并IO请求

当刷新一个脏页时，InnoDB存储引擎会该页所在区（extent）的所有页，如果是脏页，则一起进行刷新。

## InnoDB日志
InnoDB引擎有两个非常重要的日志
- 一个是undo log，
- 另外一个是redo log

undo log用来保证事务的原子性以及InnoDB的MVCC，redo log用来保证事务的持久性。

### Undo Log（逻辑日志）
Undo log一直都是事务、多版本并发控制（MVCC）的核心组件,当我们对数据记录做了修改操作时，就会记录undo log。
#### 核心功能：

- 事务回滚

    可以认为当delete一行记录时，undo log中记录的是一条对应的insert语句，当执行一条update语句时，undo log中记录的是与其相反的update语句。所以，当执行rollback时，可以从undo log的逻辑记录中获取相应的内容进行回滚。
    
- 非锁定一致性读（MVCC多行版本控制）

    行多版本控制也是通过undo log来实现的，当读取某一行被某个事务锁定时，可以通过undo log获取行在事务锁定之前的数据，从而提供行版本信息，实现非锁定一致性读取。

    每条undo log也会指向更早版本的undo log，从而形成一条更新链。通过这个更新链，不同事务可以找到其对应版本的undo log，组成old version记录，这条链就是记录的history list。

undo log的也会产生redo log记录行的物理变化

根据提交事务的行为不同，undo log 分为update undo log 和 insert undo log
- insert undo log
因为，insert操作只对事务本身可见，所以，insert undo log在事务提交后，就可以直接删除。
- update undo log
update undo log是update 和 delete操作产生的undo log。
因为是对已经存在的记录进行操作，并且update undo log还被MVCC使用，所以，当事务提交的时候，不能立刻删除update undo log。而是等待purge线程离线删除。

### redu log（物理日志）

和其他数据库一样，InnoDB记录对数据文件的物理更改，并保证总是日志先行（即WAL）。

#### 作用：数据恢复
redo log记录的是数据页的物理变化，是保证事务一致性非常重要的手段，InnoDB通过redolog保证已经commit的数据一定不会丢失，也就是事务隔离级别的持久性实现。
 
#### 跟二进制日志的区别：
 
1）二进制日志会记录所有跟MySQL有关的日志，包括InnoDB、MyISAM...，而Redo Log只记录存储引擎本身的事务日志

2）记录的内容不同，二进制日志记录的是一个事务的具体操作内容，即是逻辑日志，Redo Log记录的是每个页（page）更改的物理情况。

3）写入时间不同。二进制日志仅在事务提交前进行提交，无论该事务多大，只写磁盘一次；而在事务进行过程中，不断有Redo Log条目写入到Redo Log中。


## 索引组织表
在InnoDB存储引擎中，表都是按主键顺序组织存放的，这种存储方式组织的表称为索引组织表。

在InnoDB存储引擎中，每个表都有一个主键，如果没有显示定义主键，InnoDB会按下面的方式选择或创建主键
- 如果有非空唯一索引，则选该列为主键
- 否则，InnoDB会自动创建一个6字节的_rowid作为主键

## InnoDB逻辑存储结构
InnoDB所有数据都存储在表空间中（tablespace）。表空间又由段（segment）、区（extent）和页（page）组成。

如果用户启用innodb_file_per_talbe，则每张表的数据可以单独放在一个表空间中。

表空间是由段组成的，常见的段有数据段、索引段、回滚段。

InnoDB的表是由索引组织的，所以数据也是索引，索引也是数据。数据段即是B+Tree的叶子节点，索引段即是B+Tree的非叶子节点。对段的管理是由InnoDB引擎自身管理的。

InnoDB的区是由连续的页组成的，在任何情况下区的大小都是1M，默认情况下，InnoDB的页大小为16k，每个区64个页组成。

页是InnoDB存储引擎磁盘管理的最小单位，常见的页类型有：
- 数据页
- Undo 页
- 系统页
- 插入缓冲位图页
- 插入缓冲空闲列表页

InnoDB存储引擎是面向行的，每页存放的行记录也是硬性定义的。
InnoDB行记录格式：
- Compact （MySQL5.0引入）
- Redundant （MySQL5.0之前默认）
- Compressed
- Dynamic

Compressed 和 Dynamic是新的行格式，对于存放Blob类型的数据采用完全溢出的方式，在数据页中只存放20字节的指针，而之前的Compact 和 Redundant会存放768字节的前缀。

###  行溢出数据 
InnoDB存储引擎可以将一行记录的某些数据存储在数据页之外。一般认为大对象列类型的存储会把数据存储在页之外。

InnoDB存储引擎Verchar类型的最大长度65535（实际上跟字符集有关），这是一行中所有verchar类型的长度总和。

## MySQL分区

### MySQL支持的分区类型
- Range分区
- List分区
- Hash分区
- Key分区

当表中存在主键或者唯一索引时，分区列必须是唯一索引的一个组成部分。唯一索引是允许NULL值的，并且分区列只需要是唯一索引的一部分，不需要整个唯一索引列都是分区列。
