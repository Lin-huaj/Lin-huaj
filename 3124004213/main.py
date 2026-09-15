"""
论文查重程序
用法: python main.py <原文文件> <抄袭版文件> <答案文件>

算法概述:
    1. 读取两个文本文件，使用 utf-8 编码（忽略无法解码的字节）。
    2. 预处理：删除所有标点、空白、换行，只保留中文、英文字母和数字。
    3. 特征提取：将文本切分为连续的 2-gram（相邻两个字符组成的片段）。
    4. 相似度计算：以 2-gram 词频为向量分量，计算两个向量的余弦相似度。
    5. 输出：将重复率（0.00 ~ 1.00）写入答案文件，保留两位小数。
"""

import sys
import re
import math
from collections import Counter

# 预编译正则：匹配所有非中文、非字母、非数字的字符。
# 模块级编译避免每次调用 preprocess 时重复编译，提升性能。
_PUNCT_PATTERN = re.compile(r"[^\u4e00-\u9fa5a-zA-Z0-9]")


def read_file(path: str) -> str:
    """
    读取文件内容。

    使用 utf-8 编码，errors="ignore" 表示忽略无法解码的字节，
    避免文件中混入非法编码时程序崩溃。

    Args:
        path: 文件的绝对路径。

    Returns:
        文件的文本内容。
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def preprocess(text: str) -> str:
    """
    文本预处理：删除所有标点、空白、换行，只保留中文、字母、数字。

    这样做的目的是让比较不受标点差异的影响——抄袭版论文中常见的
    标点增删、空格调整不会干扰重复率计算。

    Args:
        text: 原始文本。

    Returns:
        仅包含中文、字母、数字的纯文本。
    """
    return _PUNCT_PATTERN.sub("", text)


def get_ngrams(text: str, n: int = 2):
    """
    将字符串切分为连续的 n 元组（n-gram）。

    中文文本使用 2-gram 效果较好：既能捕捉相邻字符的组合信息
    （比单字统计更能反映词序），又对局部增删改动有较强的鲁棒性
    （比 3-gram 更不容易因插入一个字而导致大量特征失效）。

    Args:
        text: 已预处理的文本。
        n: 窗口大小，默认为 2。

    Returns:
        n-gram 列表。空文本返回空列表；文本长度小于 n 时返回包含
        整个文本的单元素列表。
    """
    if not text:
        return []
    if len(text) < n:
        return [text]
    return [text[i:i + n] for i in range(len(text) - n + 1)]


def cosine_similarity(text1: str, text2: str, n: int = 2) -> float:
    """
    基于 n-gram 词频的余弦相似度。

    将两段文本各自映射为一个 n-gram 词频向量，然后计算两个向量
    夹角的余弦值。取值范围为 0.0 ~ 1.0：1.0 表示完全相同，
    0.0 表示毫无公共特征。

    性能优化：点积计算时始终遍历键数较少的 Counter，减少循环次数。

    Args:
        text1: 第一段已预处理文本。
        text2: 第二段已预处理文本。
        n: n-gram 窗口大小，默认为 2。

    Returns:
        0.0 ~ 1.0 之间的相似度浮点数。
    """
    grams1 = Counter(get_ngrams(text1, n))
    grams2 = Counter(get_ngrams(text2, n))

    # 任一文本为空（无任何 n-gram 特征）时，相似度为 0
    if not grams1 or not grams2:
        return 0.0

    # 性能优化：始终遍历键数较少的向量，减少点积循环次数
    if len(grams1) > len(grams2):
        grams1, grams2 = grams2, grams1

    # 向量点积：只遍历两个向量的公共键，避免构造高维稀疏全向量
    common_keys = set(grams1) & set(grams2)
    dot = sum(grams1[k] * grams2[k] for k in common_keys)

    # 向量模长
    mag1 = math.sqrt(sum(v * v for v in grams1.values()))
    mag2 = math.sqrt(sum(v * v for v in grams2.values()))

    return dot / (mag1 * mag2)


def compute_similarity(orig_path: str, copy_path: str) -> float:
    """
    对外暴露的核心接口：给定两个文件路径，返回重复率。

    该函数将文件读取、预处理、相似度计算串联起来，与命令行入口
    解耦，便于单元测试直接调用。

    Args:
        orig_path: 原文文件的绝对路径。
        copy_path: 抄袭版论文文件的绝对路径。

    Returns:
        0.0 ~ 1.0 之间的重复率。
    """
    orig_text = preprocess(read_file(orig_path))
    copy_text = preprocess(read_file(copy_path))
    return cosine_similarity(orig_text, copy_text)


def write_answer(out_path: str, ratio: float) -> None:
    """
    将重复率写入答案文件，保留两位小数。

    Args:
        out_path: 答案文件的绝对路径。
        ratio: 重复率浮点数。
    """
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"{ratio:.2f}")


def main() -> int:
    """
    命令行入口函数。

    从 sys.argv 读取三个文件路径，调用核心计算模块，将结果写入
    答案文件。对各类异常进行捕获并给出友好提示，返回退出码
    （0 表示成功，1 表示失败）。

    Returns:
        程序退出码。
    """
    # 校验命令行参数个数
    if len(sys.argv) != 4:
        print("用法: python main.py <原文文件> <抄袭版文件> <答案文件>")
        return 1

    orig_path, copy_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    # 第一阶段：计算相似度（可能因输入文件不存在而失败）
    try:
        ratio = compute_similarity(orig_path, copy_path)
    except FileNotFoundError as e:
        # 原文或抄袭版文件不存在
        print(f"文件未找到: {e}")
        return 1

    # 第二阶段：写入答案文件（可能因输出路径无效或无权限而失败）
    try:
        write_answer(out_path, ratio)
    except PermissionError as e:
        # 答案文件路径无写入权限
        print(f"权限不足，无法写入答案文件: {e}")
        return 1
    except OSError as e:
        # 其他文件读写错误（如输出路径所在目录不存在）
        print(f"文件读写错误: {e}")
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
