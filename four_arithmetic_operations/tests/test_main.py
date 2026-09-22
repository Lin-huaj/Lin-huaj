#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""main.py 的单元测试。"""

import os
import sys
import unittest
from fractions import Fraction

# 把项目根目录加入 sys.path，保证从任意位置运行都能 import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    Num, Bin, Parser,
    frac_to_str, str_to_frac,
    generate_problems, calc_answer, grade,
)


class TestFractionFormat(unittest.TestCase):
    """分数格式化与解析。"""

    def test_natural_number(self):
        self.assertEqual(frac_to_str(Fraction(4, 1)), "4")
        self.assertEqual(frac_to_str(Fraction(0, 1)), "0")

    def test_proper_fraction(self):
        self.assertEqual(frac_to_str(Fraction(3, 5)), "3/5")

    def test_mixed_number(self):
        self.assertEqual(frac_to_str(Fraction(11, 2)), "5'1/2")

    def test_str_to_frac_natural(self):
        self.assertEqual(str_to_frac("4"), Fraction(4, 1))

    def test_str_to_frac_proper(self):
        self.assertEqual(str_to_frac("3/5"), Fraction(3, 5))

    def test_str_to_frac_mixed(self):
        self.assertEqual(str_to_frac("2'3/8"), Fraction(19, 8))

    def test_roundtrip(self):
        for f in [Fraction(1, 2), Fraction(7, 3), Fraction(11, 2),
                  Fraction(0, 1), Fraction(9, 1)]:
            self.assertEqual(str_to_frac(frac_to_str(f)), f)


class TestExpressionValue(unittest.TestCase):
    """表达式计算正确性。"""

    def test_add(self):
        e = Bin("+", Num(Fraction(1, 6)), Num(Fraction(1, 8)))
        self.assertEqual(e.value(), Fraction(7, 24))

    def test_subtract(self):
        e = Bin("-", Num(Fraction(5, 4)), Num(Fraction(1, 2)))
        self.assertEqual(e.value(), Fraction(3, 4))

    def test_multiply(self):
        e = Bin("×", Num(Fraction(2, 3)), Num(Fraction(3, 4)))
        self.assertEqual(e.value(), Fraction(1, 2))

    def test_divide(self):
        e = Bin("÷", Num(Fraction(3, 4)), Num(Fraction(1, 2)))
        self.assertEqual(e.value(), Fraction(3, 2))

    def test_nested(self):
        # 1 + 2 × 3 = 7
        e = Bin("+", Num(Fraction(1)),
                    Bin("×", Num(Fraction(2)), Num(Fraction(3))))
        self.assertEqual(e.value(), 7)


class TestNormalization(unittest.TestCase):
    """去重规范化：+ 和 × 满足交换律。"""

    def test_add_commutative(self):
        a = Bin("+", Num(Fraction(23)), Num(Fraction(45)))
        b = Bin("+", Num(Fraction(45)), Num(Fraction(23)))
        self.assertEqual(a.norm_key(), b.norm_key())

    def test_mul_commutative(self):
        a = Bin("×", Num(Fraction(6)), Num(Fraction(8)))
        b = Bin("×", Num(Fraction(8)), Num(Fraction(6)))
        self.assertEqual(a.norm_key(), b.norm_key())

    def test_sub_not_commutative(self):
        a = Bin("-", Num(Fraction(10)), Num(Fraction(3)))
        b = Bin("-", Num(Fraction(3)), Num(Fraction(10)))
        self.assertNotEqual(a.norm_key(), b.norm_key())

    def test_div_not_commutative(self):
        a = Bin("÷", Num(Fraction(10)), Num(Fraction(2)))
        b = Bin("÷", Num(Fraction(2)), Num(Fraction(10)))
        self.assertNotEqual(a.norm_key(), b.norm_key())

    def test_nested_commutativity(self):
        # 3+(2+1) 和 1+2+3 应该等价
        a = Bin("+", Num(Fraction(3)),
                    Bin("+", Num(Fraction(2)), Num(Fraction(1))))
        b = Bin("+", Bin("+", Num(Fraction(1)), Num(Fraction(2))),
                    Num(Fraction(3)))
        self.assertEqual(a.norm_key(), b.norm_key())


class TestBracketRendering(unittest.TestCase):
    """括号渲染。"""

    def test_no_paren_for_mul_inside_add(self):
        # 1 + 2 × 3 不需要括号
        e = Bin("+", Num(Fraction(1)),
                    Bin("×", Num(Fraction(2)), Num(Fraction(3))))
        self.assertEqual(e.to_text(), "1 + 2 × 3")

    def test_paren_for_add_inside_mul(self):
        # 4 × (1/3 + 6) 需要括号
        e = Bin("×", Num(Fraction(4)),
                    Bin("+", Num(Fraction(1, 3)), Num(Fraction(6))))
        self.assertEqual(e.to_text(), "4 × (1/3 + 6)")

    def test_paren_for_sub_after_sub(self):
        # a - (b - c) 需要括号
        e = Bin("-", Num(Fraction(10)),
                    Bin("-", Num(Fraction(5)), Num(Fraction(3))))
        self.assertEqual(e.to_text(), "10 - (5 - 3)")

    def test_no_paren_for_chain_add(self):
        e = Bin("+", Bin("+", Num(Fraction(1)), Num(Fraction(2))),
                    Num(Fraction(3)))
        self.assertEqual(e.to_text(), "1 + 2 + 3")


class TestParser(unittest.TestCase):
    """题目解析（用于判题）。"""

    def test_parse_simple(self):
        self.assertEqual(calc_answer("1 + 2 × 3 ="), 7)

    def test_parse_paren(self):
        self.assertEqual(calc_answer("(1 + 2) × 3 ="), 9)

    def test_parse_fraction(self):
        self.assertEqual(calc_answer("1/6 + 1/8 ="), Fraction(7, 24))

    def test_parse_mixed(self):
        # 2'1/2 + 1/2 = 3
        self.assertEqual(calc_answer("2'1/2 + 1/2 ="), 3)

    def test_parse_chain(self):
        # 1 - (4/5 - 4/9) = 29/45
        self.assertEqual(calc_answer("1 - (4/5 - 4/9) ="),
                         Fraction(29, 45))


class TestGenerator(unittest.TestCase):
    """题目生成约束。"""

    def test_count_and_range(self):
        problems = generate_problems(50, r=10, seed=42)
        self.assertEqual(len(problems), 50)

    def test_no_duplicates(self):
        problems = generate_problems(200, r=15, seed=1)
        keys = set()
        for eq, _ in problems:
            node = Parser(eq).parse()
            k = node.norm_key()
            self.assertNotIn(k, keys, f"重复题目: {eq}")
            keys.add(k)

    def test_operator_count_le_3(self):
        problems = generate_problems(100, r=10, seed=2)
        for eq, _ in problems:
            node = Parser(eq).parse()
            self.assertLessEqual(node.op_count(), 3)

    def test_no_negative_result(self):
        problems = generate_problems(200, r=10, seed=3)
        for eq, ans in problems:
            self.assertGreaterEqual(str_to_frac(ans), 0,
                                   f"出现负数答案: {eq} -> {ans}")


class TestGrading(unittest.TestCase):
    """判题功能。"""

    def test_grade(self):
        # 构造临时文件
        import tempfile
        d = tempfile.mkdtemp()
        ex_path = os.path.join(d, "E.txt")
        ans_path = os.path.join(d, "A.txt")
        with open(ex_path, "w", encoding="utf-8") as f:
            f.write("  1. 1 + 1 =\n")
            f.write("  2. 2 × 3 =\n")
            f.write("  3. 1/2 + 1/2 =\n")
        with open(ans_path, "w", encoding="utf-8") as f:
            f.write("  1. 2\n")
            f.write("  2. 5\n")   # 错
            f.write("  3. 1\n")
        grade_path, correct, wrong = grade(ex_path, ans_path, dir_=d)
        self.assertEqual(correct, [1, 3])
        self.assertEqual(wrong, [2])
        with open(grade_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Correct: 2 (1, 3)", content)
        self.assertIn("Wrong: 1 (2)", content)


if __name__ == "__main__":
    unittest.main()
