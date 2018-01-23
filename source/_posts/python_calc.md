title: 'Python几个算法实现'
date: 2014-07-08 13:02:53
categories: 算法 #文章文类
tags: [算法,冒泡,python] #文章标签，多于一项时用这种格式
---

### 1.平衡点问题：
比如int[] numbers = {1,3,5,7,8,25,4,20}; 25前面的总和为24，25后面的总和也是24，25这个点就是平衡点；假如一个数组中的元素，其前面的部分等于后面的部分，那么这个点的位序就是平衡点   
要求：返回任何一个平衡点
``` bash
def balance_point(li):
    start = 0
    end = len(li)-1
    sum_start = li[start]
    sum_end = li[end]
    while start < end:
        if sum_start == sum_end and end-start == 2:
            return start+1
        if sum_start < sum_end:
            start += 1
            sum_start += li[start]
        else:
            end -= 1
            sum_end += li[end]
    return -1
```
	
 
### 2.支配点问题： 
支配数：数组中某个元素出现的次数大于数组总数的一半时就成为支配数，其所在位序成为支配点；比如int[] a = {3,3,1,2,3};3为支配数，0，1，4分别为支配点；   
要求：返回任何一个支配点

``` bash
def control_point(li):
    count_li = len(li)/2
    for i in li:
        if li.count(i) > count_li:
            return i

    return -1
```
 
### 3.python冒泡排序

*冒泡*排序是最简单且稳定的排序方式，时间复杂度为O(n*n).下面主要使用Python range()函数控制循环，以及python返回多个值的性质，使得代码很简单

```bash
def bubble_sort(li):
    for i in range(len(li)-1, 0, -1):
        for j in range(0,i):
            if li[j] > li[j+1]:
                li[j+1], li[j] = li[j], li[j+1]
```

### 4.输出1~N之间的素数

**定义**：素数又叫质数[维基百科](http://zh.wikipedia.org/wiki/%E7%B4%A0%E6%95%B0)

```bash
from math import sqrt


def sushu_out(n):
    result = []
    for num in range(2, n):
        flag = True
        for j in range(2, int(sqrt(num))+1):
            if num % j == 0:
                flag = False
                break
        if flag:
            result.append(num)
    print result, len(result)
```

### 5.删除list中重复元素

- l2 = list(set(l1))
- l2 = {}.fromkeys(l1).keys()

不改变原来顺序

- l2 = sorted(set(l1),key=l1.index)
- 遍历

### 6.斐波那契数列

**定义**：[斐波那契数列](http://zh.wikipedia.org/wiki/%E6%96%90%E6%B3%A2%E9%82%A3%E5%A5%91%E6%95%B0%E5%88%97)

```bash
def fib(n):
    ret = []
    a = 0
    b = 1
    for i in range(0, n):
        ret.append(b)      # 主意此处不能使用ret[i] = b ，会导致数组越界，因为ret现在为空，Java中数组初始化要给定长度，Python不同。
        a, b = b, a+b
    return ret
```
