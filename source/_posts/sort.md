title: '排序算法'
date: 2014-07-09 00:02:53
categories: 算法 #文章文类
tags: [算法,快排,python] #文章标签，多于一项时用这种格式
---

### 1.选择排序：
**思想**：[选择排序](http://baike.baidu.com/view/547263.htm?fr=aladdin)是简单但不稳定的排序算法，时间复杂度为O(n^2)，是选择最小（或最大）的元素插入到当前主循环位置上。
``` bash
def select_sort(li):
    for i in range(0, len(li)-1):
        min = i+1
        # 找出i+1之后元素中最下的一个
        for j in range(i+1, len(li)):
            if li[j] < li[min]:
                min = j
        # 如果后面的元素小，则交换
        if li[i] > li[min]:
            li[i], li[min] = li[min], li[i]
```
	
 
### 2.插入排序： 
**思想**：[插入排序](http://baike.baidu.com/view/396887.htm?fr=aladdin)是一种简单且稳定的排序算法，时间复杂度为O(n^2)，算法默认主循环之前的为有序，主循环之后的相继找到他应在的位置，保证主循环之前有序，直到循环结束。

``` bash
def insert_sort(li):
    for i in range(1, len(li)):
        # 这里需要注意range函数在倒序的时候 获取最后（也就是索引为0）的元素时 end 要用-1 使用0总是落下第一个元素
        # 调试了很长时间 谨记
        for j in range(i-1, -1, -1):
            if li[j] > li[j+1]:
                li[j], li[j+1] = li[j+1], li[j]
```
 
### 3.快速排序

[快速排序](http://baike.baidu.com/view/19016.htm?from_id=2084344&type=syn&fromtitle=%E5%BF%AB%E9%80%9F%E6%8E%92%E5%BA%8F&fr=aladdin)是对冒泡排序的改进，时间复杂度为O(n*log2n).基本思想是：通过一趟排序将要排序的数据分割成独立的两部分，其中一部分的所有数据都比另外一部分的所有数据都要小，然后再按此方法对这两部分数据分别进行快速排序，整个排序过程可以递归进行，以此达到整个数据变成有序序列。

```bash
# 将数组中元素按某个默认元素key分开，其前面的元素都小于key，其后面元素都大于key，返回key所在的索引
def divide_two(li, low, high):
    flag = li[low]
    while low < high:
        while low < high and li[high] > flag:
            high -= 1
        if low < high:
            li[low] = li[high]
            low += 1

        while low < high and li[low] < flag:
            low += 1
        if low < high:
            li[high] = li[low]
            high -= 1
    li[low] = flag
    return low

# 递归调用，完成排序
def quick_sort(li, low, high):
    if low < high:
        mid = divide_two(li, low, high)
        quick_sort(li, 0, mid-1)
        quick_sort(li, mid+1, high)
```

