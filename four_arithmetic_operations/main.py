#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小学四则运算题目生成器（命令行版）

用法：
  生成题目：  python main.py -n 10 -r 10
  判题：      python main.py -e Exercises.txt -a Answers.txt

输出文件（位于当前工作目录）：
  Exercises.txt  题目
  Answers.txt    答案
  Grade.txt      判题结果（仅判题模式）
"""

import argparse
import os
import random
import sys
from fractions import Fraction


# ============================================================
# 数值格式化：Fraction <-> 题目要求的字符串
# ============================================================

def frac_to_str(f: Fraction) -> str:
    """把 Fraction 转成题目要求的字符串。
    4/1   -> '4'
    3/5   -> '3/5'
    11/2  -> '5'1/2'
    """
    if f.denominator == 1:
        return str(f.numerator)
    whole = f.numerator // f.denominator
    rem = f.numerator % f.denominator
    if whole == 0:
        return f"{f.numerator}/{f.denominator}"
    return f"{whole}'{rem}/{f.denominator}"


def str_to_frac(s: str) -> Fraction:
    """把题目中的数值字符串解析为 Fraction。"""
    s = s.strip()
    if "'" in s:
        whole, frac = s.split("'", 1)
        num, den = frac.split("/")
        return Fraction(int(whole) * int(den) + int(num), int(den))
    if "/" in s:
        num, den = s.split("/")
        return Fraction(int(num), int(den))
    return Fraction(int(s), 1)


# ============================================================
# 表达式 AST
# ============================================================

class Node:
    """表达式节点基类。"""
    def value(self) -> Fraction: ...
    def norm_key(self) -> str: ...
    def to_text(self) -> str: ...
    def op_count(self) -> int: ...


class Num(Node):
    def __init__(self, v: Fraction):
        self.v = v

    def value(self):
        return self.v

    def norm_key(self):
        return "N" + str(self.v)

    def to_text(self):
        return frac_to_str(self.v)

    def op_count(self):
        return 0


class Bin(Node):
    def __init__(self, op: str, left: Node, right: Node):
        self.op = op
        self.left = left
        self.right = right

    def value(self):
        a, b = self.left.value(), self.right.value()
        if self.op == "+":
            return a + b
        if self.op == "-":
            return a - b
        if self.op == "×":
            return a * b
        if self.op == "÷":
            return a / b
        raise ValueError(f"未知运算符 {self.op}")

    def norm_key(self):
        """规范化 key：对 + 和 × 交换左右子树，用于去重。"""
        l, r = self.left.norm_key(), self.right.norm_key()
        if self.op in ("+", "×"):
            if l > r:
                l, r = r, l
        return f"({self.op}{l}{r})"

    def op_count(self):
        return 1 + self.left.op_count() + self.right.op_count()

    def to_text(self):
        prec = {"+": 1, "-": 1, "×": 2, "÷": 2}
        p = prec[self.op]
        lt = self.left.to_text()
        rt = self.right.to_text()

        lp = _prec(self.left)
        rp = _prec(self.right)

        # 左子树：同优先级左结合，不需要括号；优先级低才需要
        left_paren = isinstance(self.left, Bin) and lp < p
        # 右子树：优先级低需要括号；同优先级时，- 和 ÷ 也需要括号
        right_paren = isinstance(self.right, Bin) and (
            rp < p or (rp == p and self.op in ("-", "÷"))
        )

        if left_paren:
            lt = f"({lt})"
        if right_paren:
            rt = f"({rt})"
        return f"{lt} {self.op} {rt}"


def _prec(node: Node) -> int:
    if isinstance(node, Bin):
        return {"+": 1, "-": 1, "×": 2, "÷": 2}[node.op]
    return 3  # 数字最高


# ============================================================
# 随机生成
# ============================================================

def rand_number(rng: random.Random, r: int) -> Fraction:
    """在 [0, r) 范围内随机生成一个数（自然数、真分数或带分数）。"""
    choices = ["nat"]
    if r >= 3:
        choices += ["proper", "mixed"]
    kind = rng.choice(choices)

    if kind == "nat":
        return Fraction(rng.randint(0, r - 1), 1)

    if kind == "proper":
        # 真分数：分子 < 分母，分母 < r
        den = rng.randint(2, r - 1)
        num = rng.randint(1, den - 1)
        return Fraction(num, den)

    # 带分数：整数部分 < r，分数部分为真分数
    whole = rng.randint(1, r - 1)
    den = rng.randint(2, r - 1)
    num = rng.randint(1, den - 1)
    return Fraction(whole * den + num, den)


def gen_expr(rng: random.Random, r: int, max_ops: int) -> Node:
    """随机生成一个最多含 max_ops 个运算符的表达式。

    约束：
      - 减法左值 >= 右值（过程不产生负数）
      - 除法右值 != 0
      - 除法结果用 Fraction 精确表示（天然为分数）
    """
    # 不再分配运算符：直接返回叶子
    if max_ops <= 0:
        return Num(rand_number(rng, r))

    op = rng.choice(["+", "-", "×", "÷"])

    # 分配左右子树的运算符配额
    if max_ops == 1:
        left_ops = right_ops = 0
    else:
        left_ops = rng.randint(0, max_ops - 1)
        right_ops = max_ops - 1 - left_ops

    left = gen_expr(rng, r, left_ops)

    # 生成 right，按 op 约束重试
    for _ in range(80):
        right = gen_expr(rng, r, right_ops)
        if op == "-" and left.value() < right.value():
            continue
        if op == "÷" and right.value() == 0:
            continue
        # 除法结果必须是分数（Fraction 天然满足）；
        # 额外约束：结果分母不要过大，避免出现 1/2+1/3=5/6 后再除出怪异结果
        return Bin(op, left, right)

    # 兜底：80 次重试仍不满足约束时，改用最安全的运算符/右值
    if op == "-":
        # 减法：右值取 0（left >= 0 恒成立，不会产生负数）
        right = Num(Fraction(0, 1))
        return Bin("-", left, right)
    if op == "÷":
        # 除法：范围内找不到非零右值（如 r=1）时，退化为加法 a + 0
        right = Num(Fraction(0, 1))
        return Bin("+", left, right)
    # + / × 兜底：随机一个数即可
    right = Num(rand_number(rng, r))
    return Bin(op, left, right)


def generate_problems(n: int, r: int, seed: int = None):
    """生成 n 道不重复的题目，返回 [(expr_text, answer_str), ...]。"""
    if r < 1:
        raise ValueError("-r 必须是正整数")
    rng = random.Random(seed)
    seen = set()
    problems = []
    max_retries = n * 200  # 足够大的重试上限
    retries = 0

    while len(problems) < n and retries < max_retries:
        retries += 1
        max_ops = rng.randint(1, 3)
        try:
            node = gen_expr(rng, r, max_ops)
        except RecursionError:
            continue
        # 去掉极端情况：结果为负（理论上不会发生）或除法分母为 0
        try:
            val = node.value()
        except ZeroDivisionError:
            continue
        if val < 0:
            continue
        key = node.norm_key()
        if key in seen:
            continue
        seen.add(key)
        problems.append((node.to_text() + " =", frac_to_str(val)))

    if len(problems) < n:
        raise RuntimeError(
            f"在 r={r} 范围内只能生成 {len(problems)} 道不重复题目，"
            f"无法达到要求的 {n} 道。请增大 -r 参数。"
        )
    return problems


# ============================================================
# 题目解析（判题模式用）
# ============================================================

class Parser:
    """递归下降解析器：把题目文本解析为表达式树。"""

    def __init__(self, text: str):
        self.s = text.strip().rstrip("=").strip()
        self.i = 0

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else None

    def skip_space(self):
        while self.i < len(self.s) and self.s[self.i].isspace():
            self.i += 1

    def parse(self) -> Node:
        node = self.parse_add()
        return node

    def parse_add(self) -> Node:
        left = self.parse_mul()
        while True:
            self.skip_space()
            c = self.peek()
            if c in ("+", "-"):
                self.i += 1
                right = self.parse_mul()
                left = Bin(c, left, right)
            else:
                break
        return left

    def parse_mul(self) -> Node:
        left = self.parse_atom()
        while True:
            self.skip_space()
            c = self.peek()
            if c in ("×", "÷"):
                self.i += 1
                right = self.parse_atom()
                left = Bin(c, left, right)
            else:
                break
        return left

    def parse_atom(self) -> Node:
        self.skip_space()
        c = self.peek()
        if c == "(":
            self.i += 1
            node = self.parse_add()
            self.skip_space()
            if self.peek() != ")":
                raise ValueError(f"缺少右括号，位置 {self.i}: {self.s!r}")
            self.i += 1
            return node
        return Num(self.parse_number())

    def parse_number(self) -> Fraction:
        self.skip_space()
        start = self.i
        while self.i < len(self.s) and self.s[self.i].isdigit():
            self.i += 1
        # 带分数： n'num/den
        if self.peek() == "'":
            self.i += 1
            while self.i < len(self.s) and self.s[self.i].isdigit():
                self.i += 1
            if self.peek() != "/":
                raise ValueError("带分数缺少 /")
            self.i += 1
            while self.i < len(self.s) and self.s[self.i].isdigit():
                self.i += 1
        elif self.peek() == "/":
            # 真分数：num/den
            self.i += 1
            while self.i < len(self.s) and self.s[self.i].isdigit():
                self.i += 1
        return str_to_frac(self.s[start:self.i])


def calc_answer(problem_text: str) -> Fraction:
    """根据题目文本重新计算答案。"""
    return Parser(problem_text).parse().value()


# ============================================================
# 文件读写
# ============================================================

def write_exercises_and_answers(problems, dir_="."):
    ex_path = os.path.join(dir_, "Exercises.txt")
    ans_path = os.path.join(dir_, "Answers.txt")
    with open(ex_path, "w", encoding="utf-8") as fex, \
         open(ans_path, "w", encoding="utf-8") as fans:
        for i, (eq, ans) in enumerate(problems, 1):
            fex.write(f"{i:>3}. {eq}\n")
            fans.write(f"{i:>3}. {ans}\n")
    return ex_path, ans_path


def read_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [ln.rstrip("\n").rstrip("\r") for ln in f if ln.strip()]


def grade(ex_file: str, ans_file: str, dir_="."):
    ex_lines = read_lines(ex_file)
    ans_lines = read_lines(ans_file)
    n = min(len(ex_lines), len(ans_lines))

    correct = []
    wrong = []
    for i in range(n):
        # 去掉行首的编号 "  1. "
        ex_text = _strip_number_prefix(ex_lines[i])
        user_ans_text = _strip_number_prefix(ans_lines[i])
        try:
            right_ans = calc_answer(ex_text)
            user_ans = str_to_frac(user_ans_text)
            ok = (right_ans == user_ans)
        except Exception:
            ok = False
        if ok:
            correct.append(i + 1)
        else:
            wrong.append(i + 1)

    grade_path = os.path.join(dir_, "Grade.txt")
    with open(grade_path, "w", encoding="utf-8") as f:
        f.write(f"Correct: {len(correct)} ({', '.join(map(str, correct))})\n")
        f.write(f"Wrong: {len(wrong)} ({', '.join(map(str, wrong))})\n")
    return grade_path, correct, wrong


def _strip_number_prefix(line: str) -> str:
    """去掉题目/答案行首的 '  1. ' 编号。"""
    s = line.strip()
    # 形如 "1. xxx" 或 "  1. xxx"
    dot = s.find(". ")
    if dot > 0 and s[:dot].strip().isdigit():
        return s[dot + 1:].strip()
    return s


# ============================================================
# 命令行入口
# ============================================================

HELP = """小学四则运算题目生成器

用法：
  生成题目：  python main.py -n <题目个数> -r <数值范围>
  判题：      python main.py -e <题目文件> -a <答案文件>

参数：
  -n  生成题目数量（如 -n 10）
  -r  数值范围，自然数/真分数/真分数分母均小于该值（必选，如 -r 10）
  -e  题目文件路径（判题模式）
  -a  答案文件路径（判题模式）
"""


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="小学四则运算题目生成器",
        add_help=False,
    )
    parser.add_argument("-n", type=int, default=None)
    parser.add_argument("-r", type=int, default=None)
    parser.add_argument("-e", "--exercise", type=str, default=None)
    parser.add_argument("-a", "--answer", type=str, default=None)
    parser.add_argument("-h", "--help", action="store_true")

    args = parser.parse_args(argv)

    if args.help:
        print(HELP)
        return 0

    # 判题模式
    if args.exercise and args.answer:
        if not os.path.isfile(args.exercise):
            print(f"错误：找不到题目文件 {args.exercise}", file=sys.stderr)
            return 1
        if not os.path.isfile(args.answer):
            print(f"错误：找不到答案文件 {args.answer}", file=sys.stderr)
            return 1
        grade_path, correct, wrong = grade(args.exercise, args.answer)
        print(f"判题完成：正确 {len(correct)} 道，错误 {len(wrong)} 道")
        print(f"结果已写入 {grade_path}")
        return 0

    # 生成模式
    if args.n is None:
        print("错误：生成题目时必须指定 -n 参数", file=sys.stderr)
        print(HELP, file=sys.stderr)
        return 1
    if args.r is None:
        print("错误：必须指定 -r 参数（数值范围）", file=sys.stderr)
        print(HELP, file=sys.stderr)
        return 1
    if args.r < 1:
        print("错误：-r 必须是正整数", file=sys.stderr)
        return 1
    if args.n < 1:
        print("错误：-n 必须是正整数", file=sys.stderr)
        return 1

    problems = generate_problems(args.n, args.r)
    ex_path, ans_path = write_exercises_and_answers(problems)
    print(f"已生成 {len(problems)} 道题目：")
    print(f"  题目文件：{ex_path}")
    print(f"  答案文件：{ans_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
