"""Skyscrapers logic puzzle: generator + backtracking solver.

规则：在 n×n 网格里每行每列填入 1..n（拉丁方），
四周的线索数字表示从该方向看过去能看到的"楼"数
（高的楼会挡住后面矮的楼）。
"""

import argparse
import itertools
import random
import sys


def visible_count(line):
    """从一侧看过去能看到的楼数。"""
    best = 0
    seen = 0
    for h in line:
        if h > best:
            best = h
            seen += 1
    return seen


def clues_of(grid):
    """由完整拉丁方算出四周线索：top/bottom/left/right 各 n 个。"""
    n = len(grid)
    top = [visible_count([grid[r][c] for r in range(n)]) for c in range(n)]
    bottom = [visible_count([grid[r][c] for r in range(n - 1, -1, -1)]) for c in range(n)]
    left = [visible_count(row) for row in grid]
    right = [visible_count(row[::-1]) for row in grid]
    return {"top": top, "bottom": bottom, "left": left, "right": right}


def check_solution(grid, clues):
    """验证拉丁方 + 全部非空线索（0 表示被挖掉的线索，不校验）。"""
    n = len(grid)
    want = set(range(1, n + 1))
    for row in grid:
        if set(row) != want:
            return False
    for c in range(n):
        if {grid[r][c] for r in range(n)} != want:
            return False
    full = clues_of(grid)
    for side in ("top", "bottom", "left", "right"):
        for i, v in enumerate(clues[side]):
            if v and full[side][i] != v:
                return False
    return True


def solve(clues, size, max_nodes=2_000_000):
    """回溯求解；返回第一个解或 None。"""
    n = size
    top, bottom = clues["top"], clues["bottom"]
    left, right = clues["left"], clues["right"]

    # 预计算每行的全部排列（n<=5 时可行：5!=120）
    perms = list(itertools.permutations(range(1, n + 1)))
    row_cands = []
    for r in range(n):
        ok = []
        for p in perms:
            if left[r] and visible_count(p) != left[r]:
                continue
            if right[r] and visible_count(p[::-1]) != right[r]:
                continue
            ok.append(p)
        row_cands.append(ok)

    grid = [None] * n
    nodes = [0]

    def col_ok(c, upto):
        col = [grid[r][c] for r in range(upto)]
        if len(set(col)) != len(col):
            return False
        return True

    def full_col_ok(c):
        col = [grid[r][c] for r in range(n)]
        if top[c] and visible_count(col) != top[c]:
            return False
        if bottom[c] and visible_count(col[::-1]) != bottom[c]:
            return False
        return True

    def rec(r):
        nodes[0] += 1
        if nodes[0] > max_nodes:
            return None
        if r == n:
            if all(full_col_ok(c) for c in range(n)):
                return [list(row) for row in grid]
            return None
        for p in row_cands[r]:
            grid[r] = p
            if all(col_ok(c, r + 1) for c in range(n)):
                res = rec(r + 1)
                if res is not None:
                    return res
        grid[r] = None
        return None

    return rec(0)


def random_latin(n, rng):
    """回溯生成随机拉丁方；失败则换顺序重试。"""
    for _ in range(200):
        grid = [[0] * n for _ in range(n)]

        def rec(r, c):
            if r == n:
                return True
            nr, nc = (r, c + 1) if c + 1 < n else (r + 1, 0)
            used = {grid[r][j] for j in range(n)} | {grid[i][c] for i in range(n)}
            vals = [v for v in range(1, n + 1) if v not in used]
            rng.shuffle(vals)
            for v in vals:
                grid[r][c] = v
                if rec(nr, nc):
                    return True
            grid[r][c] = 0
            return False

        if rec(0, 0):
            return grid
    raise RuntimeError("拉丁方生成失败（200 次重试）")


def generate(size, seed=None, mask_prob=0.35):
    """生成谜题：随机拉丁方算出线索，再按概率挖掉部分线索。"""
    rng = random.Random(seed)
    grid = random_latin(size, rng)
    clues = clues_of(grid)
    masked = {}
    for side in ("top", "bottom", "left", "right"):
        masked[side] = [0 if rng.random() < mask_prob else v for v in clues[side]]
    return masked, grid


def render_puzzle(clues, size):
    n = size
    lines = []
    lines.append("     " + "  ".join(str(v) if v else "·" for v in clues["top"]))
    lines.append("   +" + "---" * n + "+")
    for r in range(n):
        l = str(clues["left"][r]) if clues["left"][r] else "·"
        rr = str(clues["right"][r]) if clues["right"][r] else "·"
        lines.append(f" {l} |" + "   " * n + f"| {rr}")
    lines.append("   +" + "---" * n + "+")
    lines.append("     " + "  ".join(str(v) if v else "·" for v in clues["bottom"]))
    return "\n".join(lines)


def render_solution(grid):
    return "\n".join(" ".join(str(v) for v in row) for row in grid)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skyscrapers", description="摩天楼逻辑谜题：生成与求解")
    ap.add_argument("--size", type=int, choices=[4, 5], default=4, help="棋盘大小")
    ap.add_argument("--seed", type=int, default=None, help="随机种子")
    ap.add_argument("--show-solution", action="store_true", help="同时显示答案")
    args = ap.parse_args(argv)

    clues, answer = generate(args.size, args.seed)
    print(f"摩天楼 {args.size}×{args.size}（种子={args.seed}）：\n")
    print(render_puzzle(clues, args.size))
    if args.show_solution:
        print("\n答案：")
        print(render_solution(answer))
        # 自证：答案满足谜题线索
        assert check_solution(answer, clues), "内部错误：生成的答案不满足线索"
        print("\n（已验证：答案满足全部线索）")


if __name__ == "__main__":
    sys.exit(main())
