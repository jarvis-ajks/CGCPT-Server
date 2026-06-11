# -*- coding: utf-8 -*-
"""
layer_generator.py — 密堆积层状结构生成器核心模块（无GUI版本）

从 CGCPT-main 项目的 stack_main.py 提取的 LayeredXOGenerator 类，
去除了 Tkinter GUI 部分，仅保留核心算法逻辑。

本版整合修改：
1. M7层的M原子网格由相邻主层的X原子网格决定。
2. XB3O6层单独使用特殊ABC平移向量：
   A -> (0, 0)
   B -> (7/(3*nx), 7/(3*ny))
   C -> (14/(3*nx), 14/(3*ny))
3. 当M层夹在XB3O6层之间时，M层也使用同样的特殊ABC平移向量。
4. 其他层仍使用原始ABC平移向量：
   A -> (0, 0)
   B -> (1/(3*nx), 1/(3*ny))
   C -> (2/(3*nx), 2/(3*ny))
5. 取消翻转判定。XBO3、BO3 层固定使用默认 B 位，不再翻转。
6. M6 层由 M7 层删除对应位置原子得到，不再独立生成固定模板。
7. M6 层在执行偏移操作时，使用对应的 M7 参考网格，而不是 M6 自身删点后的网格。
"""

import numpy as np
import math
from fractions import Fraction


def frac_mod(coord):
    return tuple((np.array(coord) % 1.0).tolist())


def unique_frac_coords(coords, ndigits=8):
    uniq = []
    seen = set()
    for c in coords:
        c_rounded = np.round(c, ndigits)
        c_mod = c_rounded % 1.0
        key = tuple(0.0 if x == 0.0 else x for x in c_mod)
        if key not in seen:
            seen.add(key)
            uniq.append(key)
    return uniq


def parse_number_or_fraction(value):
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        raise ValueError("空字符串无法解析为数值")
    if "/" in s:
        try:
            return float(Fraction(s))
        except Exception as e:
            raise ValueError(f"无法解析分数字符串: {value}") from e
    try:
        return float(s)
    except Exception as e:
        raise ValueError(f"无法解析数值字符串: {value}") from e


class LayeredXOGenerator:
    def __init__(
        self,
        x_element="Ba",
        o_element="O",
        m_element="Mg",
        t_element="Si",
        b_element="B",
        target_xo_distance=2.77648,
        nx=6,
        ny=6,
        enable_t=True,
    ):
        self.x_element = x_element
        self.o_element = o_element
        self.m_element = m_element
        self.t_element = t_element
        self.b_element = b_element

        self.target_xo_distance = float(target_xo_distance)
        self.layer_spacing = (np.sqrt(2) / np.sqrt(3)) * self.target_xo_distance

        self.nx = int(nx)
        self.ny = int(ny)
        self.enable_t = enable_t

    def is_main_layer(self, mode):
        return mode in ["XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6"]

    def is_x_layer(self, mode):
        return mode.upper().strip() in ["XO", "XO2", "XO3", "X", "XBO3", "XB3O6"]

    def is_m_layer(self, mode):
        return mode == "M6" or mode == "M7"

    def mode_base_length(self, mode):
        mode = mode.upper().strip()
        d = self.target_xo_distance
        if mode == "XO":
            return d
        elif mode == "XO2":
            return np.sqrt(3.0) * d
        elif mode in ["XO3", "X", "XBO3", "BO3", "XB3O6"]:
            return 2.0 * d
        else:
            raise ValueError(f"未知模式: {mode}")

    def choose_inplane_length(self, layer_modes):
        main_modes = [m.upper().strip() for m in layer_modes if self.is_main_layer(m)]
        if not main_modes:
            raise ValueError("序列中必须至少包含一个主层 (如 XO, XO3 等)。")

        prio1_modes = {"XO3", "X", "XBO3", "BO3", "XB3O6"}
        prio2_modes = {"XO2"}
        prio3_modes = {"XO"}

        if any(m in prio1_modes for m in main_modes):
            base_len = 2.0 * self.target_xo_distance
            ref_mode = "XO3族系 (X/XBO3/BO3/XO3/XB3O6)"
        elif any(m in prio2_modes for m in main_modes):
            base_len = np.sqrt(3.0) * self.target_xo_distance
            ref_mode = "XO2层"
        elif any(m in prio3_modes for m in main_modes):
            base_len = self.target_xo_distance
            ref_mode = "XO层"
        else:
            base_len = self.target_xo_distance
            ref_mode = "默认基准层"

        vals = [self.mode_base_length(m) for m in main_modes]
        all_same = all(abs(v - vals[0]) < 1e-10 for v in vals)

        return base_len, all_same, ref_mode

    def get_shift_map(self):
        return {
            "A": np.array([0.0, 0.0]),
            "B": np.array([1 / (3 * self.nx), 1 / (3 * self.ny)]),
            "C": np.array([2 / (3 * self.nx), 2 / (3 * self.ny)]),
        }

    def get_special_xb3o6_shift_map(self):
        return {
            "A": np.array([0.0, 0.0]),
            "B": np.array([7 / (3 * self.nx), 7 / (3 * self.ny)]),
            "C": np.array([14 / (3 * self.nx), 14 / (3 * self.ny)]),
        }

    def _find_adjacent_main_indices(self, current_idx, layer_modes):
        n = len(layer_modes)

        prev_idx = (current_idx - 1) % n
        while not self.is_main_layer(layer_modes[prev_idx]):
            prev_idx = (prev_idx - 1) % n
            if prev_idx == current_idx:
                raise ValueError("无法找到前侧主层。")

        next_idx = (current_idx + 1) % n
        while not self.is_main_layer(layer_modes[next_idx]):
            next_idx = (next_idx + 1) % n
            if next_idx == current_idx:
                raise ValueError("无法找到后侧主层。")

        return prev_idx, next_idx

    def is_m_layer_between_xb3o6(self, current_idx, layer_modes):
        if layer_modes is None or current_idx is None:
            return False
        if not self.is_m_layer(layer_modes[current_idx]):
            return False

        prev_idx, next_idx = self._find_adjacent_main_indices(current_idx, layer_modes)
        prev_mode = layer_modes[prev_idx].upper().strip()
        next_mode = layer_modes[next_idx].upper().strip()

        return prev_mode == "XB3O6" and next_mode == "XB3O6"

    def get_shift_map_for_mode(self, mode, layer_modes=None, current_idx=None):
        mode = mode.upper().strip()

        if mode == "XB3O6":
            return self.get_special_xb3o6_shift_map()

        if self.is_m_layer(mode) and self.is_m_layer_between_xb3o6(current_idx, layer_modes):
            return self.get_special_xb3o6_shift_map()

        return self.get_shift_map()

    def _rationalize(self, x, max_den=10000):
        x = float(x) % 1.0
        return Fraction(x).limit_denominator(max_den)

    def _infer_axis_grid_from_values(self, values, max_den=10000):
        vals = sorted(set(float(v) % 1.0 for v in values))
        if len(vals) <= 1:
            return 1

        fracs = [self._rationalize(v, max_den=max_den) for v in vals]
        dens = [f.denominator for f in fracs]

        grid = dens[0]
        for d in dens[1:]:
            grid = math.lcm(grid, d)

        return max(1, grid)

    def infer_grid_from_sites(self, sites, max_den=10000):
        if not sites:
            return 1, 1

        xs = [p[0] % 1.0 for p in sites]
        ys = [p[1] % 1.0 for p in sites]

        gx = self._infer_axis_grid_from_values(xs, max_den=max_den)
        gy = self._infer_axis_grid_from_values(ys, max_den=max_den)
        return gx, gy

    def wrap_delta(self, a, b):
        d = (a - b) % 1.0
        if d > 0.5:
            d -= 1.0
        return d

    def same_position_mod1(self, p, q, tol=1e-6):
        return abs(self.wrap_delta(p[0], q[0])) < tol and abs(self.wrap_delta(p[1], q[1])) < tol

    def apply_translation(self, sites, shift_vec):
        if shift_vec[0] == 0.0 and shift_vec[1] == 0.0:
            return unique_frac_coords(sites)
        return unique_frac_coords([(x + shift_vec[0], y + shift_vec[1]) for x, y in sites])

    def rotate_frac_coords(self, coords, theta_deg, base_len):
        if theta_deg == 0.0:
            return coords
        theta_rad = np.radians(theta_deg)
        cos_t = np.cos(theta_rad)
        sin_t = np.sin(theta_rad)

        a = self.nx * base_len
        b = self.ny * base_len
        gamma_rad = np.radians(60)
        cos_g = np.cos(gamma_rad)
        sin_g = np.sin(gamma_rad)

        rotated_coords = []
        for x_f, y_f in coords:
            x_c = x_f * a + y_f * b * cos_g
            y_c = y_f * b * sin_g

            xr_c = x_c * cos_t - y_c * sin_t
            yr_c = x_c * sin_t + y_c * cos_t

            yr_f = yr_c / (b * sin_g)
            xr_f = (xr_c - yr_f * b * cos_g) / a
            rotated_coords.append((xr_f % 1.0, yr_f % 1.0))

        return unique_frac_coords(rotated_coords)

    def normalize_stack_sequence(self, stack_text, n_main_layers):
        stack_text = stack_text.strip().upper().replace(",", "").replace(" ", "")
        if len(stack_text) == 0:
            raise ValueError("堆叠序列不能为空")
        for ch in stack_text:
            if ch not in ["A", "B", "C"]:
                raise ValueError("堆叠序列只能包含 A, B, C")
        if len(stack_text) < n_main_layers:
            times = n_main_layers // len(stack_text)
            rem = n_main_layers % len(stack_text)
            stack_text = stack_text * times + stack_text[:rem]
        elif len(stack_text) > n_main_layers:
            stack_text = stack_text[:n_main_layers]
        return list(stack_text)

    def third_shift(self, s1, s2):
        all_shifts = {"A", "B", "C"}
        if s1 == s2:
            raise ValueError("两个主层 shift 相同，无法唯一确定第三个三角中心。")
        remain = list(all_shifts - {s1, s2})
        return remain[0]

    def infer_m_shift_from_adjacent_main_shifts(self, lower_shift, upper_shift):
        lower_shift = lower_shift.upper().strip()
        upper_shift = upper_shift.upper().strip()

        valid = {"A", "B", "C"}
        if lower_shift not in valid or upper_shift not in valid:
            raise ValueError(f"非法堆叠标签: {lower_shift}, {upper_shift}")

        if lower_shift == upper_shift:
            return lower_shift

        pair = {lower_shift, upper_shift}
        if pair == {"A", "B"}:
            return "C"
        if pair == {"B", "C"}:
            return "A"
        if pair == {"A", "C"}:
            return "B"

        raise ValueError(f"无法根据上下主层堆叠方式确定 M 层堆叠: {lower_shift}, {upper_shift}")

    def build_full_shift_sequence_without_T(self, layer_modes, stack_sequence_text):
        n = len(layer_modes)
        x_layers_count = sum(1 for m in layer_modes if self.is_x_layer(m))
        x_shifts = (
            self.normalize_stack_sequence(stack_sequence_text, x_layers_count)
            if x_layers_count > 0
            else []
        )

        full_shift_sequence = [None] * n
        main_shifts = []
        x_idx = 0
        current_shift = "A"
        for i, mode in enumerate(layer_modes):
            if self.is_main_layer(mode):
                if self.is_x_layer(mode):
                    current_shift = x_shifts[x_idx]
                    x_idx += 1
                full_shift_sequence[i] = current_shift
                main_shifts.append(current_shift)

        for i, mode in enumerate(layer_modes):
            if self.is_m_layer(mode):
                prev_idx, next_idx = self._find_adjacent_main_indices(i, layer_modes)

                prev_shift = full_shift_sequence[prev_idx]
                next_shift = full_shift_sequence[next_idx]

                if prev_shift is None or next_shift is None:
                    raise ValueError(f"M层索引 {i} 两侧主层的堆叠方式尚未确定。")

                m_shift = self.infer_m_shift_from_adjacent_main_shifts(prev_shift, next_shift)
                full_shift_sequence[i] = m_shift

        return full_shift_sequence, main_shifts

    def insert_T_layers(
        self, layer_modes, shift_sequence, z_sequence, layer_angles, layer_dxs, layer_dys
    ):
        if not self.enable_t:
            return layer_modes, shift_sequence, z_sequence, layer_angles, layer_dxs, layer_dys

        n = len(layer_modes)
        insertion_after = {}
        for i, mode in enumerate(layer_modes):
            if not self.is_main_layer(mode):
                continue
            left_idx = (i - 1) % n
            right_idx = (i + 1) % n
            left_mode = layer_modes[left_idx]
            right_mode = layer_modes[right_idx]

            if self.is_m_layer(left_mode) and self.is_main_layer(right_mode):
                insertion_after[i] = "left"
            if self.is_m_layer(right_mode) and self.is_main_layer(left_mode):
                insertion_after[left_idx] = "right"

        new_modes, new_shifts, new_zs, new_angles, new_dxs, new_dys = [], [], [], [], [], []
        c_frac_full = 1.0

        for i in range(n):
            new_modes.append(layer_modes[i])
            new_shifts.append(shift_sequence[i])
            new_zs.append(z_sequence[i])
            new_angles.append(layer_angles[i])
            new_dxs.append(layer_dxs[i])
            new_dys.append(layer_dys[i])

            if i in insertion_after:
                j = (i + 1) % n
                left_shift = shift_sequence[i]
                right_shift = shift_sequence[j]

                t_shift = (
                    left_shift
                    if left_shift == right_shift
                    else self.third_shift(left_shift, right_shift)
                )

                z_left = z_sequence[i]
                z_right = z_sequence[j] if j != 0 else z_sequence[j] + c_frac_full
                delta = z_right - z_left
                z_t = (
                    (z_left + 0.25 * delta)
                    if insertion_after[i] == "left"
                    else (z_left + 0.75 * delta)
                )

                new_modes.append("T")
                new_shifts.append(t_shift)
                new_zs.append(z_t % c_frac_full)
                new_angles.append(0.0)
                new_dxs.append(0.0)
                new_dys.append(0.0)

        return new_modes, new_shifts, new_zs, new_angles, new_dxs, new_dys

    def build_z_sequence_without_T(self, layer_modes, layer_alphas):
        n = len(layer_modes)
        main_indices = [i for i, m in enumerate(layer_modes) if self.is_main_layer(m)]
        n_main = len(main_indices)
        if n_main != len(layer_alphas):
            raise ValueError("Alpha系数数组长度与主层数量不匹配。")

        c = sum(layer_alphas) * self.layer_spacing
        main_z_cart = {}
        current_z = 0.0
        for i, main_idx in enumerate(main_indices):
            main_z_cart[main_idx] = current_z
            current_z += layer_alphas[i] * self.layer_spacing

        z_cart = [0.0] * n
        for i, mode in enumerate(layer_modes):
            if self.is_main_layer(mode):
                z_cart[i] = main_z_cart[i]
            elif self.is_m_layer(mode):
                prev_idx = (i - 1) % n
                next_idx = (i + 1) % n

                if not self.is_main_layer(layer_modes[prev_idx]) or not self.is_main_layer(
                    layer_modes[next_idx]
                ):
                    raise ValueError(f"M6/M7 间隙层异常 (索引 {i})：间隙层必须位于两个主层之间。")

                z_prev = main_z_cart[prev_idx]
                z_next = main_z_cart[next_idx]

                if prev_idx > i:
                    z_prev -= c
                if next_idx < i:
                    z_next += c

                z_mid = 0.5 * (z_prev + z_next)
                z_cart[i] = z_mid % c
            else:
                raise ValueError(f"未知的原始层模式: {mode}")

        z_frac = [z / c for z in z_cart]
        return z_frac, c

    def get_reference_x_sites_for_main_layer(self, mode, theta=0.0, base_len=None):
        mode = mode.upper().strip()
        zero_shift = np.array([0.0, 0.0])

        if mode == "XO":
            x_sites, _ = self.get_layer_sites_XO(zero_shift, is_special_xo=False, t_shift_vec=None)
        elif mode == "XO2":
            x_sites, _ = self.get_layer_sites_XO2(zero_shift)
        elif mode == "XO3":
            x_sites, _ = self.get_layer_sites_XO3(zero_shift)
        elif mode in ["X", "XBO3", "XB3O6"]:
            x_sites, _, _ = self.get_layer_sites_X_family(
                mode, zero_shift, flip_b_site=False, base_len=base_len
            )
        elif mode == "BO3":
            x_sites = []
        else:
            x_sites = []

        if theta != 0.0 and len(x_sites) > 0:
            x_sites = self.rotate_frac_coords(x_sites, theta, base_len)

        return list(x_sites)

    def find_adjacent_x_sites_for_M7(self, current_idx, layer_modes, layer_angles, base_len):
        if layer_modes is None or current_idx is None:
            raise ValueError("生成 M7 层时必须提供 layer_modes 和 current_idx。")

        prev_idx, next_idx = self._find_adjacent_main_indices(current_idx, layer_modes)

        prev_mode = layer_modes[prev_idx]
        prev_theta = layer_angles[prev_idx] if layer_angles is not None else 0.0
        ref_x_sites = self.get_reference_x_sites_for_main_layer(
            prev_mode, theta=prev_theta, base_len=base_len
        )

        if len(ref_x_sites) > 0:
            return ref_x_sites

        next_mode = layer_modes[next_idx]
        next_theta = layer_angles[next_idx] if layer_angles is not None else 0.0
        ref_x_sites = self.get_reference_x_sites_for_main_layer(
            next_mode, theta=next_theta, base_len=base_len
        )

        if len(ref_x_sites) > 0:
            return ref_x_sites

        raise ValueError("M7层两侧相邻主层均未提供可用的 X 原子网格参考。")

    def get_layer_sites_XO(self, shift_vec, is_special_xo=False, t_shift_vec=None):
        x_sites_A, o_sites_A, x_sites_special, o_sites_special = [], [], [], []
        for i in range(self.nx):
            for j in range(self.ny):
                base = np.array([i / self.nx, j / self.ny])
                if is_special_xo and t_shift_vec is not None:
                    x_sites_special.append((base[0], base[1]))
                    o_sites_special.append((base[0] + t_shift_vec[0], base[1] + t_shift_vec[1]))
                else:
                    if (i + j) % 2 == 0:
                        x_sites_A.append((base[0], base[1]))
                    else:
                        o_sites_A.append((base[0], base[1]))
        if is_special_xo:
            return self.apply_translation(x_sites_special, shift_vec), self.apply_translation(
                o_sites_special, shift_vec
            )
        return self.apply_translation(x_sites_A, shift_vec), self.apply_translation(
            o_sites_A, shift_vec
        )

    def get_layer_sites_XO2(self, shift_vec):
        x_sites_A, o_sites_A = [], []
        for i in range(self.nx):
            for j in range(self.ny):
                base = np.array([i / self.nx, j / self.ny])
                x_sites_A.append((base[0], base[1]))
                o1 = base + np.array([1 / (3 * self.nx), 1 / (3 * self.ny)])
                o2 = base + np.array([2 / (3 * self.nx), 2 / (3 * self.ny)])
                o_sites_A.extend([(o1[0], o1[1]), (o2[0], o2[1])])
        return self.apply_translation(x_sites_A, shift_vec), self.apply_translation(
            o_sites_A, shift_vec
        )

    def get_layer_sites_XO3(self, shift_vec):
        x_sites_A, o_sites_A = [], []
        directions = {
            "d1": np.array([1 / self.nx, 0.0]),
            "d2": np.array([0.0, 1 / self.ny]),
            "d3": np.array([1 / self.nx, -1 / self.ny]),
        }
        for i in range(self.nx):
            for j in range(self.ny):
                base = np.array([i / self.nx, j / self.ny])
                x_sites_A.append((base[0], base[1]))
                for d in directions.values():
                    o_sites_A.append((base[0] + 0.5 * d[0], base[1] + 0.5 * d[1]))
        return self.apply_translation(x_sites_A, shift_vec), self.apply_translation(
            o_sites_A, shift_vec
        )

    def get_layer_sites_X_family(self, mode, shift_vec, flip_b_site=False, base_len=None):
        x_sites_A, b_sites_A, o_sites_A = [], [], []

        if base_len is None:
            base_len = self.target_xo_distance

        scale = int(round(base_len / self.target_xo_distance))
        if scale < 1:
            scale = 1

        directions = {
            "d1": np.array([1 / self.nx, 0.0]),
            "d2": np.array([0.0, 1 / self.ny]),
            "d3": np.array([1 / self.nx, -1 / self.ny]),
        }

        if mode in ["X", "XBO3", "BO3"]:
            for i in range(self.nx):
                for j in range(self.ny):
                    base = np.array([i / self.nx, j / self.ny])
                    if mode in ["X", "XBO3"]:
                        x_sites_A.append((base[0], base[1]))
                    if mode in ["XBO3", "BO3"]:
                        b_pos = base + np.array([1 / (3 * self.nx), 1 / (3 * self.ny)])
                        b_sites_A.append((b_pos[0], b_pos[1]))
                        for d in directions.values():
                            o_sites_A.append((base[0] + 0.5 * d[0], base[1] + 0.5 * d[1]))

        elif mode == "XB3O6":
            grid_nx = self.nx * scale
            grid_ny = self.ny * scale

            grid_atoms = {}

            for i in range(grid_nx):
                for j in range(grid_ny):
                    if (i + 3 * j) % 7 == 0:
                        grid_atoms[(i, j)] = "X"
                        x_sites_A.append((i / grid_nx, j / grid_ny))
                    else:
                        grid_atoms[(i, j)] = "O"
                        o_sites_A.append((i / grid_nx, j / grid_ny))

            for i in range(grid_nx):
                for j in range(grid_ny):
                    if not flip_b_site:
                        pts = [
                            (i % grid_nx, j % grid_ny),
                            ((i + 1) % grid_nx, j % grid_ny),
                            ((i + 2) % grid_nx, j % grid_ny),
                            (i % grid_nx, (j + 1) % grid_ny),
                            ((i + 1) % grid_nx, (j + 1) % grid_ny),
                            (i % grid_nx, (j + 2) % grid_ny),
                        ]
                        if all(grid_atoms.get(pt) == "O" for pt in pts):
                            b1 = ((i + 1 / 3) / grid_nx, (j + 1 / 3) / grid_ny)
                            b2 = ((i + 4 / 3) / grid_nx, (j + 1 / 3) / grid_ny)
                            b3 = ((i + 1 / 3) / grid_nx, (j + 4 / 3) / grid_ny)
                            b_sites_A.extend([b1, b2, b3])
                    else:
                        pts = [
                            (i % grid_nx, j % grid_ny),
                            ((i - 1) % grid_nx, j % grid_ny),
                            ((i - 2) % grid_nx, j % grid_ny),
                            (i % grid_nx, (j - 1) % grid_ny),
                            ((i - 1) % grid_nx, (j - 1) % grid_ny),
                            (i % grid_nx, (j - 2) % grid_ny),
                        ]
                        if all(grid_atoms.get(pt) == "O" for pt in pts):
                            b1 = ((i - 1 / 3) / grid_nx, (j - 1 / 3) / grid_ny)
                            b2 = ((i - 4 / 3) / grid_nx, (j - 1 / 3) / grid_ny)
                            b3 = ((i - 1 / 3) / grid_nx, (j - 4 / 3) / grid_ny)
                            b_sites_A.extend([b1, b2, b3])

        return (
            self.apply_translation(x_sites_A, shift_vec),
            self.apply_translation(b_sites_A, shift_vec),
            self.apply_translation(o_sites_A, shift_vec),
        )

    def get_layer_sites_T(self, shift_vec):
        sites_A = []
        for i in range(self.nx):
            for j in range(self.ny):
                base = np.array([i / self.nx, j / self.ny])
                sites_A.append((base[0], base[1]))
        return self.apply_translation(sites_A, shift_vec)

    def get_layer_sites_M7_from_adjacent_X(self, ref_x_sites, shift_vec):
        if not ref_x_sites:
            raise ValueError("M7层无法生成：相邻主层中未找到可用的 X 原子网格参考。")
        return self.apply_translation(list(ref_x_sites), shift_vec)

    def get_layer_sites_M6(
        self,
        center_shift_label,
        lattice,
        layer_modes=None,
        layer_angles=None,
        current_idx=None,
        base_len=None,
    ):
        shift_vec = self.get_shift_map_for_mode(
            "M6", layer_modes=layer_modes, current_idx=current_idx
        )[center_shift_label]

        ref_x_sites = self.find_adjacent_x_sites_for_M7(
            current_idx=current_idx,
            layer_modes=layer_modes,
            layer_angles=layer_angles,
            base_len=base_len,
        )

        all_m7_sites = self.get_layer_sites_M7_from_adjacent_X(ref_x_sites, np.array([0.0, 0.0]))
        if len(all_m7_sites) == 0:
            raise ValueError("M6层无法生成：对应的M7参考位点为空。")

        gx, gy = self.infer_grid_from_sites(all_m7_sites)
        kept_sites = []

        for x, y in all_m7_sites:
            i = int(round((x % 1.0) * gx)) % gx
            j = int(round((y % 1.0) * gy)) % gy
            if (i - j) % 3 != 0:
                kept_sites.append((x, y))

        return self.apply_translation(kept_sites, shift_vec)

    def get_reference_grid_sites_for_layer(
        self,
        mode,
        x_sites,
        b_sites,
        o_sites,
        m_sites,
        t_sites,
        layer_modes=None,
        layer_angles=None,
        current_idx=None,
        base_len=None,
    ):
        mode_u = mode.upper().strip()

        if mode_u == "M6":
            ref_x_sites = self.find_adjacent_x_sites_for_M7(
                current_idx=current_idx,
                layer_modes=layer_modes,
                layer_angles=layer_angles,
                base_len=base_len,
            )
            return self.get_layer_sites_M7_from_adjacent_X(ref_x_sites, np.array([0.0, 0.0]))

        if self.is_main_layer(mode_u):
            if len(x_sites) > 0:
                return list(x_sites)
            all_sites = []
            all_sites.extend(x_sites)
            all_sites.extend(b_sites)
            all_sites.extend(o_sites)
            return all_sites

        if self.is_m_layer(mode_u):
            return list(m_sites)

        if mode_u == "T":
            return list(t_sites)

        all_sites = []
        all_sites.extend(x_sites)
        all_sites.extend(b_sites)
        all_sites.extend(o_sites)
        all_sites.extend(m_sites)
        all_sites.extend(t_sites)
        return all_sites

    def build_user_translation_vec_from_sites(self, sites, dx_steps, dy_steps):
        gx, gy = self.infer_grid_from_sites(sites)
        return np.array([dx_steps / gx, dy_steps / gy], dtype=float)

    def build_total_shift_vec_from_sites(
        self,
        sites,
        shift_label,
        dx_steps=0.0,
        dy_steps=0.0,
        mode=None,
        layer_modes=None,
        current_idx=None,
    ):
        if mode is None:
            shift_base = self.get_shift_map()[shift_label]
        else:
            shift_base = self.get_shift_map_for_mode(
                mode, layer_modes=layer_modes, current_idx=current_idx
            )[shift_label]
        return shift_base + self.build_user_translation_vec_from_sites(sites, dx_steps, dy_steps)

    def get_layer_sites(
        self,
        mode,
        shift_label,
        lattice=None,
        is_special_xo=False,
        t_shift_vec=None,
        flip_b_site=False,
        base_len=None,
        layer_modes=None,
        layer_angles=None,
        current_idx=None,
    ):
        mode = mode.upper().strip()
        shift_vec = self.get_shift_map_for_mode(
            mode, layer_modes=layer_modes, current_idx=current_idx
        )[shift_label]

        if mode in ["X", "XBO3", "BO3", "XB3O6"]:
            return self.get_layer_sites_X_family(
                mode, shift_vec, flip_b_site=flip_b_site, base_len=base_len
            )

        elif self.is_m_layer(mode):
            if mode == "M7":
                ref_x_sites = self.find_adjacent_x_sites_for_M7(
                    current_idx=current_idx,
                    layer_modes=layer_modes,
                    layer_angles=layer_angles,
                    base_len=base_len,
                )
                return self.get_layer_sites_M7_from_adjacent_X(ref_x_sites, shift_vec)
            else:
                return self.get_layer_sites_M6(
                    shift_label,
                    lattice,
                    layer_modes=layer_modes,
                    layer_angles=layer_angles,
                    current_idx=current_idx,
                    base_len=base_len,
                )

        elif mode == "T":
            return self.get_layer_sites_T(shift_vec)

        else:
            if mode == "XO":
                return self.get_layer_sites_XO(shift_vec, is_special_xo, t_shift_vec)
            elif mode == "XO2":
                return self.get_layer_sites_XO2(shift_vec)
            elif mode == "XO3":
                return self.get_layer_sites_XO3(shift_vec)

        raise ValueError(f"无法匹配的层模式: {mode}")
