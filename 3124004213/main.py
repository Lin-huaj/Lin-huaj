"""
论文查重程序
用法: python main.py <原文文件> <抄袭版文件> <答案文件>
"""

import sys
import re
import math
from collections import Counter


def read_file(path: str) -> str:
    """读取文件内容，使用 utf-8 编码，忽略无法解码的字符。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def preprocess(text: str) -> str:
    """
    预处理：去掉所有标点、空白、换行，只保留中文、字母、数字。
    这样比较时不会受标点差异影响。
    """
    return re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)


def get_ngrams(text: str, n: int = 2):
    """把字符串切成连续的 n 元组（中文用 2-gram 效果较好）。"""
    if not text:
        return []
    if len(text) < n:
        return [text]
    return [text[i:i + n] for i in range(len(text) - n + 1)]


def cosine_similarity(text1: str, text2: str, n: int = 2) -> float:
    """
    基于 n-gram 词频的余弦相似度，返回 0.0 ~ 1.0 之间的浮点数。
    """
    grams1 = Counter(get_ngrams(text1, n))
    grams2 = Counter(get_ngrams(text2, n))

    if not grams1 or not grams2:
        return 0.0

    # 向量点积
    common_keys = set(grams1) & set(grams2)
    dot = sum(grams1[k] * grams2[k] for k in common_keys)

    # 模长
    mag1 = math.sqrt(sum(v * v for v in grams1.values()))
    mag2 = math.sqrt(sum(v * v for v in grams2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)


def compute_similarity(orig_path: str, copy_path: str) -> float:
    """对外暴露的接口：给两个文件路径，返回重复率。"""
    orig_text = preprocess(read_file(orig_path))
    copy_text = preprocess(read_file(copy_path))
    return cosine_similarity(orig_text, copy_text)


def write_answer(out_path: str, ratio: float) -> None:
    """把结果写进答案文件，保留两位小数。"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"{ratio:.2f}")


def main() -> int:
    if len(sys.argv) != 4:
        print("用法: python main.py <原文文件> <抄袭版文件> <答案文件>")
        return 1

    orig_path, copy_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]

    try:
        ratio = compute_similarity(orig_path, copy_path)
    except FileNotFoundError as e:
        print(f"文件未找到: {e}")
        return 1

    write_answer(out_path, ratio)
    return 0


if __name__ == "__main__":
    sys.exit(main())