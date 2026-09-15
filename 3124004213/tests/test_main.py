"""
论文查重程序单元测试
运行方式: python -m pytest tests --cov=main --cov-report=term-missing
"""
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
    main,
    read_file,
)


# ---------- 基础函数测试 ----------

def test_preprocess_removes_punctuation():
    """预处理应删除中文和英文标点。"""
    assert preprocess("今天，天气晴！") == "今天天气晴"


def test_preprocess_keeps_alnum():
    """预处理应保留字母和数字，删除特殊符号。"""
    assert preprocess("abc123！@#") == "abc123"


def test_get_ngrams_short_text():
    """文本长度小于 n 时，返回包含整个文本的单元素列表。"""
    assert get_ngrams("a", 2) == ["a"]


def test_get_ngrams_length_equals_n():
    """文本长度恰好等于 n 时，返回包含整个文本的单元素列表。"""
    assert get_ngrams("ab", 2) == ["ab"]


def test_get_ngrams_normal():
    """正常长度文本的 2-gram 切分结果应精确正确。"""
    assert get_ngrams("abcd", 2) == ["ab", "bc", "cd"]


def test_get_ngrams_empty():
    """空文本应返回空列表。"""
    assert get_ngrams("", 2) == []


# ---------- 相似度测试 ----------

def test_identical_text_similarity_is_one():
    """完全相同的文本相似度应为 1.0。"""
    a = preprocess("今天是星期天，天气晴。")
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_completely_different_texts():
    """完全无公共 2-gram 的文本相似度应为 0.0。"""
    a = preprocess("abcabcabcabc")
    b = preprocess("xyxyxyxyxyxy")
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_empty_text_returns_zero():
    """任一文本为空时，相似度应为 0.0 且不抛异常。"""
    assert cosine_similarity("", "abc") == 0.0
    assert cosine_similarity("abc", "") == 0.0
    assert cosine_similarity("", "") == 0.0


def test_partial_overlap_between_zero_and_one():
    """部分重叠的文本（增删改抄袭样例）相似度应介于 0 和 1 之间。"""
    a = preprocess("今天是星期天，天气晴，晚上看电影")
    b = preprocess("今天是周天，天气晴朗，晚上去看电影")
    sim = cosine_similarity(a, b)
    assert 0.0 < sim < 1.0


def test_similarity_symmetric():
    """余弦相似度应满足对称性：sim(a, b) == sim(b, a)。"""
    a = preprocess("我爱北京天安门")
    b = preprocess("我爱北京故宫")
    assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(b, a))


# ---------- 文件级测试 ----------

def test_compute_similarity_with_files():
    """通过临时文件验证 compute_similarity 文件级接口。"""
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
    """答案文件应输出保留两位小数的浮点数字符串。"""
    out = tmp_path / "ans.txt"
    write_answer(str(out), 0.876)
    with open(out, "r", encoding="utf-8") as f:
        assert f.read() == "0.88"


# ---------- 异常处理测试 ----------

def test_main_wrong_arg_count_returns_1(monkeypatch, capsys):
    """场景：命令行参数个数不是 3 个，应打印用法说明并返回 1。"""
    monkeypatch.setattr(sys, "argv", ["main.py", "only_one_arg"])
    rc = main()
    assert rc == 1
    assert "用法" in capsys.readouterr().out


def test_main_missing_file_returns_1(monkeypatch, capsys, tmp_path):
    """场景：原文文件不存在，应捕获 FileNotFoundError 并返回 1。"""
    out = tmp_path / "ans.txt"
    monkeypatch.setattr(sys, "argv", [
        "main.py",
        str(tmp_path / "not_exist.txt"),
        str(tmp_path / "copy.txt"),
        str(out),
    ])
    rc = main()
    assert rc == 1
    assert "文件未找到" in capsys.readouterr().out


def test_main_output_path_invalid_returns_1(monkeypatch, capsys, tmp_path):
    """场景：答案文件所在目录不存在，应捕获 OSError 并返回 1。"""
    orig = tmp_path / "orig.txt"
    copy = tmp_path / "copy.txt"
    orig.write_text("今天天气晴", encoding="utf-8")
    copy.write_text("今天天气晴朗", encoding="utf-8")
    bad_out = tmp_path / "no_such_dir" / "ans.txt"

    monkeypatch.setattr(sys, "argv", ["main.py", str(orig), str(copy), str(bad_out)])
    rc = main()
    assert rc == 1
    assert "文件读写错误" in capsys.readouterr().out


def test_main_permission_denied_returns_1(monkeypatch, capsys, tmp_path):
    """场景：答案文件为只读，应捕获 PermissionError 并返回 1。"""
    import stat
    orig = tmp_path / "orig.txt"
    copy = tmp_path / "copy.txt"
    orig.write_text("今天天气晴", encoding="utf-8")
    copy.write_text("今天天气晴朗", encoding="utf-8")

    # 创建一个只读文件作为输出路径
    read_only = tmp_path / "readonly.txt"
    read_only.write_text("", encoding="utf-8")
    os.chmod(str(read_only), stat.S_IREAD)  # 设为只读

    try:
        monkeypatch.setattr(sys, "argv", ["main.py", str(orig), str(copy), str(read_only)])
        rc = main()
        assert rc == 1
        assert "权限不足" in capsys.readouterr().out
    finally:
        # 恢复写权限以便临时目录正常清理
        os.chmod(str(read_only), stat.S_IWRITE | stat.S_IREAD)


def test_read_file_ignores_invalid_utf8(tmp_path):
    """场景：文件包含非法 UTF-8 字节，errors='ignore' 应保证读取不抛异常。"""
    p = tmp_path / "garbled.txt"
    p.write_bytes(
        "今天天气晴".encode("utf-8")
        + b"\xff\xfe\x00"
        + "晚上看电影".encode("utf-8")
    )
    text = read_file(str(p))
    assert "今天天气晴" in text
    assert "晚上看电影" in text
