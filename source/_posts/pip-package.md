title: 'pip安装python环境及打包'
date: 2014-06-26 09:37:53
categories: Python #文章文类
tags: [pip,打包,python] #文章标签，多于一项时用这种格式
---
### 0.安装虚拟环境
``` bash
pip install virtualenv
virtualenv env1
source env1/bin/activate
```
	
 
### 1. 将包依赖信息保存在requirements.txt文件

``` bash
pip freeze > requirements.txt
```
 
### 2.根据依赖文件安装依赖

```bash
pip install -r requirements.txt
```
 
### 3.根据依赖文件下载依赖包

```bash
pip install -d /path/to/save/ -r requirements.txt
```
 
### 4.pip install -i指定pypi服务器

```bash
pip install -i http://127.0.0.1:8000/ -r requirements.txt
```
 
### 5.打/opt/tools/env中所有依赖包到MyEnv.pybundle

```bash
pip bundle  MyEnv.pybundle -r pip-requires --no-index -f /opt/tools/env
```
 
### 6.使用MyEnv.pybundle安装依赖包

```bash
pip install MyEnv.pybundle
```

