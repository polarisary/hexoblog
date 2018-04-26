---
title: Python Web流程
date: 2018-02-08 20:40:41
categories: Python
tags: [Python,Web]
---

### 流程上大概分三层：
  1. web服务器层
      a. 主要包括Nginx、Apache等
  2. WSGI层
      a. Web Server Gateway Interface，定义了 web服务器和 web应用之间的接口规范
  3. web 应用层
      a. 主要包括Flash、Django等
![三层关系](1.png)

### 几个相关概念：
**CGI(Common Gateway Inteface)**:外部应用程序与Web服务器之间的接口标准

**FastCGI**: CGI的一个扩展， 提升了性能，废除了 CGI fork-and-execute （来一个请求 fork 一个新进程处理，处理完再把进程 kill 掉）的工作方式，转而使用一种长生存期的方法，减少了进程消耗，提升了性能。

**WSGI（Python Web Server GateWay Interface）**:它是用在 python web 框架编写的应用程序与后端服务器之间的规范（本例就是 Django 和 uWSGI 之间），让你写的应用程序可以与后端服务器顺利通信。在 WSGI 出现之前你不得不专门为某个后端服务器而写特定的 API，并且无法更换后端服务器，而 WSGI 就是一种统一规范， 所有使用 WSGI 的服务器都可以运行使用 WSGI 规范的 web 框架，反之亦然。

**uWSGI**: 是一个Web服务器，它实现了WSGI协议、uwsgi、http等协议。用于接收前端服务器转发的动态请求并处理后发给 web 应用程序。

**uwsgi**: 是uWSGI服务器实现的独有的协议， 网上没有明确的说明这个协议是用在哪里的，我个人认为它是用于前端服务器与 uWSGI 的通信规范，相当于 FastCGI的作用。
  - WSGI看过前面小节的同学很清楚了，是一种通信协议。
  - uwsgi同WSGI一样是一种通信协议。
  - 而uWSGI是实现了uwsgi和WSGI两种协议的Web服务器。
![协议](2.png)