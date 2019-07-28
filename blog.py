#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import logging.config
import argparse
import time
import requests
from tomd import Tomd

from bs4 import BeautifulSoup

blog_domain = "http://mysql.taobao.org"


def main_page():
    r = requests.get( blog_domain + "/monthly/", headers=headers)
    r.encoding='utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    # print (len(soup.select('.posts')))
    for link in soup.select('.posts')[0].find_all('a'):
    	month_page(link.get('href'))

def month_page(month):
    r = requests.get(blog_domain+month, headers=headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    # print (soup.prettify())
    for link in soup.select('.posts')[0].find_all('a'):
        href_arr = link.get('href').split('/')
        print (href_arr)

        if(int(href_arr[2]) > 2017):
            print("SKIP 2 --- " + str(int(href_arr[2])))
            continue
        else:
            if(int(href_arr[2]) == 2017):
                if (int(href_arr[3]) > 2):
                    print("SKIP 3 --- "+str(int(href_arr[3])))
                    continue
                if(int(href_arr[3]) == 2 and int(href_arr[4]) < 3):
                    print("SKIP 4 --- " + str(int(href_arr[4])))
                    continue
        # print ("--->"+link.get('href'))
        blog(link.get('href'))


def blog(addr):
    r = requests.get(blog_domain+addr, headers=headers)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, 'html.parser')
    blog_title = soup.title.string
    file_name = blog_title.replace('  ', '-')
    file_name = file_name.replace(' ', '-')
    file_name = file_name.replace('.', '-')
    file_name = file_name.replace('/', '-')
    file_name = file_name.replace('+', '-')
    file_name = file_name.replace('_', '-')
    file_name = file_name.replace('(', '')
    file_name = file_name.replace(')', '')
    print (addr)
    # hexo new
    os.system('hexo new "{}"'.format(file_name))
    time.sleep(0.5);
    blog_title_arr = blog_title.split('·')
    blog_header = '''
---
title: {}
date: 2018-09-28 15:47:45
categories: [alidb-monthly, {}, {}]
tags: [{}, {}]
---
    '''.format(blog_title, blog_title_arr[0].strip(), blog_title_arr[1].strip(), blog_title_arr[0].strip(), blog_title_arr[1].strip())
    blog_footer = '''

## 郑重声明
> 文章来自淘宝技术博客 [数据库内核月报](http://mysql.taobao.org/monthly/2017/04/01/)
> 
> 本人为了学习方便而分类整理

    '''
    # print (soup.select('.post')[0].prettify())
    # print (blog_header + Tomd(str(soup.select('.post')[0])).markdown)
    write_file(file_name + '.md', blog_header + Tomd(str(soup.select('.post')[0])).markdown + blog_footer)

def write_file(file_name, content):
    file_path = './source/_posts/'
    with open(file_path+file_name, 'wt') as f:
        f.truncate()
        f.write(content)

if __name__ == '__main__':
    headers = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36', 'X-DevTools-Emulate-Network-Conditions-Client-Id': '853B53D93401C5EACDE50E409FCB0612', 'Upgrade-Insecure-Requests': '1'}
    # blog('/monthly/2018/07/02/')
    main_page()



# vim: set expandtab ts=4 sts=4 sw=4 :
