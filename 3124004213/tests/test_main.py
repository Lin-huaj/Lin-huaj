import os
import sys
import tempfile
import pytest

# 让测试能找到上一层的 main.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (  # noqa: E402
    preprocess,
    get_ngrams,
    cosine_similarity,
    compute_similarity,
    write_answer,
)


# ---------- 基础函数测试 ----------

def test_preprocess_removes_punctuation():
    assert preprocess("今天，天气晴！") == "今天天气晴"


def test_preprocess_keeps_alnum():
    assert preprocess("abc123！@#") == "abc123"


def test_get_ngrams_short_text():
    # 长度不足 n 时返回整体
    assert get_ngrams("a", 2) == ["a"]


def test_get_ngrams_normal():
    assert get_ngrams("abcd", 2) == ["ab", "bc", "cd"]


def test_get_ngrams_empty():
    assert get_ngrams("", 2) == []


# ---------- 相似度测试 ----------

def test_identical_text_similarity_is_one():
    a = preprocess("今天是星期天，天气晴。")
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_completely_different_texts():
    a = preprocess("abcabcabcabc")
    b = preprocess("xyxyxyxyxyxy")
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_empty_text_returns_zero():
    assert cosine_similarity("", "abc") == 0.0
    assert cosine_similarity("abc", "") == 0.0
    assert cosine_similarity("", "") == 0.0


def test_partial_overlap_between_zero_and_one():
    a = preprocess("今天是星期天，天气晴，晚上看电影")
    b = preprocess("今天是周天，天气晴朗，晚上去看电影")
    sim = cosine_similarity(a, b)
    assert 0.0 < sim < 1.0


def test_similarity_symmetric():
    a = preprocess("我爱北京天安门")
    b = preprocess("我爱北京故宫")
    assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


# ---------- 文件级测试 ----------

def test_compute_similarity_with_files():
    with tempfile.TemporaryDirectory() as d:
        orig = os.path.join(d, "orig.txt")
        copy = os.path.join(d, "copy.txt")
        with open(orig, "w", encoding="utf-8") as f:
            f.write("今天是星期天，天气晴，今天晚上我要去看电影。")
        with open(copy, "w", encoding="utf-8") as f:
            f.write("今天是周天，天气晴朗，我晚上要去看电影。")

        sim = compute_similarity(orig, copy)
        assert 0.0 < sim <= 1.0


def test_write_answer_format(tmp_path):
    out = tmp_path / "ans.txt"
    write_answer(str(out), 0.876)
    with open(out, "r", encoding="utf-8") as f:
        assert f.read() == "0.88"