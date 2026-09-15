# 论文查重

## 用法
python main.py <原文文件> <抄袭版文件> <答案文件>

## 示例
python main.py C:\tests\orig.txt C:\tests\orig_add.txt C:\tests\ans.txt

## 说明
- 采用 2-gram + 余弦相似度
- 输出为 0.00 ~ 1.00 的浮点数