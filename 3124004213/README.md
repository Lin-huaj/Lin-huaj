# 论文查重

基于 2-gram 词频向量与余弦相似度的论文查重程序。

## 用法

```bash
python main.py <原文文件> <抄袭版文件> <答案文件>
```

### 示例

```bash
python main.py C:\tests\orig.txt C:\tests\orig_add.txt C:\tests\ans.txt
```

## 算法

1. **读取文件**：以 utf-8 编码读取，忽略无法解码的字节。
2. **预处理**：删除所有标点、空白、换行，只保留中文、英文字母和数字。
3. **特征提取**：将文本切分为连续的 2-gram（相邻两个字符组成的片段）。
4. **相似度计算**：以 2-gram 词频为向量分量，计算两个向量的余弦相似度。
5. **输出**：将重复率（0.00 ~ 1.00）写入答案文件，保留两位小数。

## 项目结构

```
3124004213/
├── main.py              # 程序入口与核心算法
├── requirements.txt     # 依赖说明（仅使用 Python 3 标准库）
├── README.md            # 项目说明
└── tests/
    ├── test_main.py     # 单元测试（18 个用例）
    ├── orig.txt         # 测试原文（《活着》节选）
    ├── orig_0.8_add.txt # 抄袭版测试文本
    └── ans.txt          # 样例答案
```

## 测试

```bash
# 运行单元测试
python -m pytest tests -v

# 运行测试并查看覆盖率
python -m pytest tests --cov=main --cov-report=term-missing
```

## 说明

- 输出为 0.00 ~ 1.00 的浮点数，精确到小数点后两位
- 仅使用 Python 3 标准库，无需安装第三方依赖
- 测试覆盖率 98%，18 个单元测试用例全部通过
