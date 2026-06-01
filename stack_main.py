# -*- coding: utf-8 -*-
"""
密堆积层状结构生成器 (逐层自动识别网格平移版 - 包含 XB3O6 超结构)

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

本次修改：
5. 取消翻转判定。
6. XBO3、BO3 层固定使用默认 B 位，不再翻转。
7. M6 层由 M7 层删除对应位置原子得到，不再独立生成固定模板。
8. M6 层在执行偏移操作时，使用对应的 M7 参考网格，而不是 M6 自身删点后的网格。
"""

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog as fd, messagebox
import math
from fractions import Fraction

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from pymatgen.core import Lattice, Structure
from pymatgen.io.cif import CifWriter
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer


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
    """
    将字符串解析为浮点数，支持：
    1. 普通小数/整数，例如 2.66667, 60, -1.25
    2. 分数字符串，例如 8/3, 2/3, -7/2
    """
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
    def __init__(self, x_element="Ba", o_element="O", m_element="Mg", t_element="Si", b_element="B",
                 target_xo_distance=2.77648, nx=6, ny=6, enable_t=True):
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

    def _pick_grid_sites_by_mode(self, mode, x_sites, b_sites, o_sites, m_sites, t_sites):
        mode = mode.upper().strip()

        if self.is_main_layer(mode):
            if len(x_sites) > 0:
                return list(x_sites)
            all_sites = []
            all_sites.extend(x_sites)
            all_sites.extend(b_sites)
            all_sites.extend(o_sites)
            return all_sites

        if self.is_m_layer(mode):
            return list(m_sites)

        if mode == "T":
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

    def build_total_shift_vec_from_sites(self, sites, shift_label, dx_steps=0.0, dy_steps=0.0,
                                         mode=None, layer_modes=None, current_idx=None):
        if mode is None:
            shift_base = self.get_shift_map()[shift_label]
        else:
            shift_base = self.get_shift_map_for_mode(mode, layer_modes=layer_modes, current_idx=current_idx)[shift_label]
        return shift_base + self.build_user_translation_vec_from_sites(sites, dx_steps, dy_steps)

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
        x_shifts = self.normalize_stack_sequence(stack_sequence_text, x_layers_count) if x_layers_count > 0 else []

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

    def insert_T_layers(self, layer_modes, shift_sequence, z_sequence, layer_angles, layer_dxs, layer_dys):
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

                t_shift = left_shift if left_shift == right_shift else self.third_shift(left_shift, right_shift)

                z_left = z_sequence[i]
                z_right = z_sequence[j] if j != 0 else z_sequence[j] + c_frac_full
                delta = z_right - z_left
                z_t = (z_left + 0.25 * delta) if insertion_after[i] == "left" else (z_left + 0.75 * delta)

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

                if not self.is_main_layer(layer_modes[prev_idx]) or not self.is_main_layer(layer_modes[next_idx]):
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
            x_sites, _, _ = self.get_layer_sites_X_family(mode, zero_shift, flip_b_site=False, base_len=base_len)
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
        ref_x_sites = self.get_reference_x_sites_for_main_layer(prev_mode, theta=prev_theta, base_len=base_len)

        if len(ref_x_sites) > 0:
            return ref_x_sites

        next_mode = layer_modes[next_idx]
        next_theta = layer_angles[next_idx] if layer_angles is not None else 0.0
        ref_x_sites = self.get_reference_x_sites_for_main_layer(next_mode, theta=next_theta, base_len=base_len)

        if len(ref_x_sites) > 0:
            return ref_x_sites

        raise ValueError("M7层两侧相邻主层均未提供可用的 X 原子网格。")

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
            return self.apply_translation(x_sites_special, shift_vec), self.apply_translation(o_sites_special, shift_vec)
        return self.apply_translation(x_sites_A, shift_vec), self.apply_translation(o_sites_A, shift_vec)

    def get_layer_sites_XO2(self, shift_vec):
        x_sites_A, o_sites_A = [], []
        for i in range(self.nx):
            for j in range(self.ny):
                base = np.array([i / self.nx, j / self.ny])
                x_sites_A.append((base[0], base[1]))
                o1 = base + np.array([1 / (3 * self.nx), 1 / (3 * self.ny)])
                o2 = base + np.array([2 / (3 * self.nx), 2 / (3 * self.ny)])
                o_sites_A.extend([(o1[0], o1[1]), (o2[0], o2[1])])
        return self.apply_translation(x_sites_A, shift_vec), self.apply_translation(o_sites_A, shift_vec)

    def get_layer_sites_XO3(self, shift_vec):
        x_sites_A, o_sites_A = [], []
        directions = {
            "d1": np.array([1 / self.nx, 0.0]),
            "d2": np.array([0.0, 1 / self.ny]),
            "d3": np.array([1 / self.nx, -1 / self.ny])
        }
        for i in range(self.nx):
            for j in range(self.ny):
                base = np.array([i / self.nx, j / self.ny])
                x_sites_A.append((base[0], base[1]))
                for d in directions.values():
                    o_sites_A.append((base[0] + 0.5 * d[0], base[1] + 0.5 * d[1]))
        return self.apply_translation(x_sites_A, shift_vec), self.apply_translation(o_sites_A, shift_vec)

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
            "d3": np.array([1 / self.nx, -1 / self.ny])
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
                            (i % grid_nx, (j + 2) % grid_ny)
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
                            (i % grid_nx, (j - 2) % grid_ny)
                        ]
                        if all(grid_atoms.get(pt) == "O" for pt in pts):
                            b1 = ((i - 1 / 3) / grid_nx, (j - 1 / 3) / grid_ny)
                            b2 = ((i - 4 / 3) / grid_nx, (j - 1 / 3) / grid_ny)
                            b3 = ((i - 1 / 3) / grid_nx, (j - 4 / 3) / grid_ny)
                            b_sites_A.extend([b1, b2, b3])

        return (
            self.apply_translation(x_sites_A, shift_vec),
            self.apply_translation(b_sites_A, shift_vec),
            self.apply_translation(o_sites_A, shift_vec)
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

    def get_layer_sites_M6(self, center_shift_label, lattice, layer_modes=None, layer_angles=None,
                           current_idx=None, base_len=None):
        shift_vec = self.get_shift_map_for_mode("M6", layer_modes=layer_modes, current_idx=current_idx)[center_shift_label]

        ref_x_sites = self.find_adjacent_x_sites_for_M7(
            current_idx=current_idx,
            layer_modes=layer_modes,
            layer_angles=layer_angles,
            base_len=base_len
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

    def get_reference_grid_sites_for_layer(self, mode, x_sites, b_sites, o_sites, m_sites, t_sites,
                                           layer_modes=None, layer_angles=None, current_idx=None, base_len=None):
        """
        用于解释 dx,dy 时使用的参考网格。
        关键要求：
        - 对 M6，不使用 M6 自己删点后的网格tto
        - 而是使用对应 M7 的参考网格
        其他层保持原逻辑不变
        """
        mode_u = mode.upper().strip()

        if mode_u == "M6":
            ref_x_sites = self.find_adjacent_x_sites_for_M7(
                current_idx=current_idx,
                layer_modes=layer_modes,
                layer_angles=layer_angles,
                base_len=base_len
            )
            return self.get_layer_sites_M7_from_adjacent_X(ref_x_sites, np.array([0.0, 0.0]))

        return self._pick_grid_sites_by_mode(mode_u, x_sites, b_sites, o_sites, m_sites, t_sites)

    def get_layer_sites(self, mode, shift_label, lattice=None,
                        is_special_xo=False, t_shift_vec=None, flip_b_site=False,
                        base_len=None, layer_modes=None, layer_angles=None, current_idx=None):
        mode = mode.upper().strip()
        shift_vec = self.get_shift_map_for_mode(mode, layer_modes=layer_modes, current_idx=current_idx)[shift_label]

        if mode in ["X", "XBO3", "BO3", "XB3O6"]:
            return self.get_layer_sites_X_family(mode, shift_vec, flip_b_site=flip_b_site, base_len=base_len)

        elif self.is_m_layer(mode):
            if mode == "M7":
                ref_x_sites = self.find_adjacent_x_sites_for_M7(
                    current_idx=current_idx,
                    layer_modes=layer_modes,
                    layer_angles=layer_angles,
                    base_len=base_len
                )
                return self.get_layer_sites_M7_from_adjacent_X(ref_x_sites, shift_vec)
            else:
                return self.get_layer_sites_M6(
                    shift_label,
                    lattice,
                    layer_modes=layer_modes,
                    layer_angles=layer_angles,
                    current_idx=current_idx,
                    base_len=base_len
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

    def build_structure(self, layer_modes, layer_alphas, stack_sequence_text, layer_angles, layer_dxs, layer_dys):
        base_len, exact_flag, ref_mode = self.choose_inplane_length(layer_modes)
        original_shifts, main_shift_sequence = self.build_full_shift_sequence_without_T(layer_modes, stack_sequence_text)
        original_zs, c = self.build_z_sequence_without_T(layer_modes, layer_alphas)

        expanded_modes, expanded_shifts, expanded_zs, expanded_angles, expanded_dxs, expanded_dys = self.insert_T_layers(
            layer_modes, original_shifts, original_zs, layer_angles, layer_dxs, layer_dys
        )

        lattice = Lattice.from_parameters(
            a=self.nx * base_len, b=self.ny * base_len, c=c,
            alpha=90, beta=90, gamma=60
        )
        species, coords = [], []

        for idx, (mode, shift_label, z, theta, dx_val, dy_val) in enumerate(
            zip(expanded_modes, expanded_shifts, expanded_zs, expanded_angles, expanded_dxs, expanded_dys)
        ):
            is_special_xo = False
            t_shift_label = None
            t_idx = -1
            if mode == "XO" and self.enable_t:
                n_exp = len(expanded_modes)
                if expanded_modes[(idx - 1) % n_exp] == "T" and expanded_modes[(idx - 2) % n_exp] == "XO3":
                    is_special_xo, t_shift_label = True, expanded_shifts[(idx - 1) % n_exp]
                    t_idx = (idx - 1) % n_exp
                elif expanded_modes[(idx + 1) % n_exp] == "T" and expanded_modes[(idx + 2) % n_exp] == "XO3":
                    is_special_xo, t_shift_label = True, expanded_shifts[(idx + 1) % n_exp]
                    t_idx = (idx + 1) % n_exp

            flip_b_site = False

            x_sites, b_sites, o_sites, m_sites, t_sites = [], [], [], [], []
            rel_t_shift_vec = None

            if is_special_xo and t_shift_label:
                t_sites_for_grid = list(self.get_layer_sites(
                    "T", "A", base_len=base_len,
                    layer_modes=expanded_modes, layer_angles=expanded_angles, current_idx=t_idx
                ))
                t_abs_shift = self.build_total_shift_vec_from_sites(
                    t_sites_for_grid, t_shift_label, expanded_dxs[t_idx], expanded_dys[t_idx],
                    mode="T", layer_modes=expanded_modes, current_idx=t_idx
                )

                xo_raw_x, xo_raw_o = self.get_layer_sites(
                    "XO", "A",
                    is_special_xo=False,
                    t_shift_vec=None,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
                xo_sites_for_grid = list(xo_raw_x)
                if len(xo_sites_for_grid) == 0:
                    xo_sites_for_grid = list(xo_raw_x) + list(xo_raw_o)
                xo_abs_shift = self.build_total_shift_vec_from_sites(
                    xo_sites_for_grid, shift_label, dx_val, dy_val,
                    mode="XO", layer_modes=expanded_modes, current_idx=idx
                )
                rel_t_shift_vec = t_abs_shift - xo_abs_shift

            if mode in ["X", "XBO3", "BO3", "XB3O6"]:
                x_bp, b_bp, o_bp = self.get_layer_sites(
                    mode, "A",
                    flip_b_site=flip_b_site,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
                x_sites, b_sites, o_sites = x_bp, b_bp, o_bp
            elif self.is_m_layer(mode):
                m_sites = self.get_layer_sites(
                    mode, "A",
                    lattice=lattice,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
            elif mode == "T":
                t_sites = self.get_layer_sites(
                    "T", "A",
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
            else:
                x_bp, o_bp = self.get_layer_sites(
                    mode, "A",
                    is_special_xo=is_special_xo,
                    t_shift_vec=rel_t_shift_vec,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
                x_sites, o_sites = x_bp, o_bp

            if theta != 0.0:
                x_sites = self.rotate_frac_coords(x_sites, theta, base_len)
                b_sites = self.rotate_frac_coords(b_sites, theta, base_len)
                o_sites = self.rotate_frac_coords(o_sites, theta, base_len)
                m_sites = self.rotate_frac_coords(m_sites, theta, base_len)
                t_sites = self.rotate_frac_coords(t_sites, theta, base_len)

            grid_sites = self.get_reference_grid_sites_for_layer(
                mode,
                x_sites, b_sites, o_sites, m_sites, t_sites,
                layer_modes=expanded_modes,
                layer_angles=expanded_angles,
                current_idx=idx,
                base_len=base_len
            )

            target_shift_vec = self.build_total_shift_vec_from_sites(
                grid_sites, shift_label, dx_val, dy_val,
                mode=mode, layer_modes=expanded_modes, current_idx=idx
            )

            x_sites = self.apply_translation(x_sites, target_shift_vec)
            b_sites = self.apply_translation(b_sites, target_shift_vec)
            o_sites = self.apply_translation(o_sites, target_shift_vec)
            m_sites = self.apply_translation(m_sites, target_shift_vec)
            t_sites = self.apply_translation(t_sites, target_shift_vec)

            for fx, fy in x_sites:
                species.append(self.x_element)
                coords.append((fx, fy, z))
            for fx, fy in b_sites:
                species.append(self.b_element)
                coords.append((fx, fy, z))
            for fx, fy in o_sites:
                species.append(self.o_element)
                coords.append((fx, fy, z))
            for fx, fy in m_sites:
                species.append(self.m_element)
                coords.append((fx, fy, z))
            for fx, fy in t_sites:
                species.append(self.t_element)
                coords.append((fx, fy, z))

        structure = Structure(lattice=lattice, species=species, coords=coords, coords_are_cartesian=False, to_unit_cell=True)
        return (
            structure, exact_flag, base_len, layer_modes, original_shifts, original_zs,
            expanded_modes, expanded_shifts, expanded_zs, main_shift_sequence,
            expanded_angles, expanded_dxs, expanded_dys, ref_mode
        )

    def analyze_structure(self, structure):
        return {
            "x_count": sum(1 for s in structure if s.specie.symbol == self.x_element),
            "o_count": sum(1 for s in structure if s.specie.symbol == self.o_element),
            "m_count": sum(1 for s in structure if s.specie.symbol == self.m_element),
            "t_count": sum(1 for s in structure if s.specie.symbol == self.t_element),
            "b_count": sum(1 for s in structure if s.specie.symbol == self.b_element),
            "formula": structure.composition.formula,
            "a": structure.lattice.a, "b": structure.lattice.b, "c": structure.lattice.c,
            "alpha": structure.lattice.alpha, "beta": structure.lattice.beta, "gamma": structure.lattice.gamma
        }

    def get_layer_atoms_for_plot(self, expanded_modes, expanded_shifts, expanded_zs,
                                 expanded_angles, expanded_dxs, expanded_dys, base_len, lattice):
        layer_data = []
        for idx, (mode, shift_label, z, theta, dx_val, dy_val) in enumerate(
            zip(expanded_modes, expanded_shifts, expanded_zs, expanded_angles, expanded_dxs, expanded_dys)
        ):
            atoms = []
            is_special_xo = False
            t_shift_label = None
            t_idx = -1
            if mode == "XO" and self.enable_t:
                n_exp = len(expanded_modes)
                if expanded_modes[(idx - 1) % n_exp] == "T" and expanded_modes[(idx - 2) % n_exp] == "XO3":
                    is_special_xo, t_shift_label = True, expanded_shifts[(idx - 1) % n_exp]
                    t_idx = (idx - 1) % n_exp
                elif expanded_modes[(idx + 1) % n_exp] == "T" and expanded_modes[(idx + 2) % n_exp] == "XO3":
                    is_special_xo, t_shift_label = True, expanded_shifts[(idx + 1) % n_exp]
                    t_idx = (idx + 1) % n_exp

            flip_b_site = False

            x_sites, b_sites, o_sites, m_sites, t_sites = [], [], [], [], []
            rel_t_shift_vec = None
            if is_special_xo and t_shift_label:
                t_sites_for_grid = list(self.get_layer_sites(
                    "T", "A", base_len=base_len,
                    layer_modes=expanded_modes, layer_angles=expanded_angles, current_idx=t_idx
                ))
                t_abs_shift = self.build_total_shift_vec_from_sites(
                    t_sites_for_grid, t_shift_label, expanded_dxs[t_idx], expanded_dys[t_idx],
                    mode="T", layer_modes=expanded_modes, current_idx=t_idx
                )

                xo_raw_x, xo_raw_o = self.get_layer_sites(
                    "XO", "A",
                    is_special_xo=False,
                    t_shift_vec=None,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
                xo_sites_for_grid = list(xo_raw_x)
                if len(xo_sites_for_grid) == 0:
                    xo_sites_for_grid = list(xo_raw_x) + list(xo_raw_o)
                xo_abs_shift = self.build_total_shift_vec_from_sites(
                    xo_sites_for_grid, shift_label, dx_val, dy_val,
                    mode="XO", layer_modes=expanded_modes, current_idx=idx
                )

                rel_t_shift_vec = t_abs_shift - xo_abs_shift

            if mode in ["X", "XBO3", "BO3", "XB3O6"]:
                x_bp, b_bp, o_bp = self.get_layer_sites(
                    mode, "A",
                    flip_b_site=flip_b_site,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
                x_sites, b_sites, o_sites = x_bp, b_bp, o_bp
            elif self.is_m_layer(mode):
                m_sites = self.get_layer_sites(
                    mode, "A",
                    lattice=lattice,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
            elif mode == "T":
                t_sites = self.get_layer_sites(
                    "T", "A",
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
            else:
                x_bp, o_bp = self.get_layer_sites(
                    mode, "A",
                    is_special_xo=is_special_xo,
                    t_shift_vec=rel_t_shift_vec,
                    base_len=base_len,
                    layer_modes=expanded_modes,
                    layer_angles=expanded_angles,
                    current_idx=idx
                )
                x_sites, o_sites = x_bp, o_bp

            if theta != 0.0:
                x_sites = self.rotate_frac_coords(x_sites, theta, base_len)
                b_sites = self.rotate_frac_coords(b_sites, theta, base_len)
                o_sites = self.rotate_frac_coords(o_sites, theta, base_len)
                m_sites = self.rotate_frac_coords(m_sites, theta, base_len)
                t_sites = self.rotate_frac_coords(t_sites, theta, base_len)

            grid_sites = self.get_reference_grid_sites_for_layer(
                mode,
                x_sites, b_sites, o_sites, m_sites, t_sites,
                layer_modes=expanded_modes,
                layer_angles=expanded_angles,
                current_idx=idx,
                base_len=base_len
            )

            target_shift_vec = self.build_total_shift_vec_from_sites(
                grid_sites, shift_label, dx_val, dy_val,
                mode=mode, layer_modes=expanded_modes, current_idx=idx
            )

            x_sites = self.apply_translation(x_sites, target_shift_vec)
            b_sites = self.apply_translation(b_sites, target_shift_vec)
            o_sites = self.apply_translation(o_sites, target_shift_vec)
            m_sites = self.apply_translation(m_sites, target_shift_vec)
            t_sites = self.apply_translation(t_sites, target_shift_vec)

            for fx, fy in x_sites:
                atoms.append((self.x_element, fx, fy))
            for fx, fy in b_sites:
                atoms.append((self.b_element, fx, fy))
            for fx, fy in o_sites:
                atoms.append((self.o_element, fx, fy))
            for fx, fy in m_sites:
                atoms.append((self.m_element, fx, fy))
            for fx, fy in t_sites:
                atoms.append((self.t_element, fx, fy))

            gx, gy = self.infer_grid_from_sites(grid_sites)

            layer_data.append({
                "mode": mode,
                "shift": shift_label,
                "z": z,
                "theta": theta,
                "dx": dx_val,
                "dy": dy_val,
                "grid_x": gx,
                "grid_y": gy,
                "atoms": atoms
            })
        return layer_data


class XOApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("晶体堆叠生成器 (自动识别网格平移版 - 含 XB3O6)")
        self.root.geometry("1080x830")
        self.structure = None

        self.enable_t_var = tk.BooleanVar(value=True)
        self.enable_b_var = tk.BooleanVar(value=True)
        self.allow_non_neutral_var = tk.BooleanVar(value=False)

        self.build_input_frame()
        self.build_output_frame()
        self.build_button_frame()
        self.toggle_t_b()
        self.root.mainloop()

    def build_input_frame(self):
        frm = tk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        tk.Label(frm, text="X:").grid(row=0, column=0, sticky="e")
        self.x_var = tk.StringVar(value="Ba")
        tk.Entry(frm, textvariable=self.x_var, width=6).grid(row=0, column=1, padx=1, sticky="w")

        tk.Label(frm, text="O:").grid(row=0, column=2, sticky="e")
        self.o_var = tk.StringVar(value="O")
        tk.Entry(frm, textvariable=self.o_var, width=6).grid(row=0, column=3, padx=1, sticky="w")

        tk.Label(frm, text="M:").grid(row=0, column=4, sticky="e")
        self.m_var = tk.StringVar(value="Mg")
        tk.Entry(frm, textvariable=self.m_var, width=6).grid(row=0, column=5, padx=1, sticky="w")

        tk.Label(frm, text="T:").grid(row=0, column=6, sticky="e")
        self.t_var = tk.StringVar(value="Si")
        self.t_entry = tk.Entry(frm, textvariable=self.t_var, width=6)
        self.t_entry.grid(row=0, column=7, padx=1, sticky="w")

        tk.Label(frm, text="B:").grid(row=0, column=8, sticky="e")
        self.b_var = tk.StringVar(value="B")
        self.b_entry = tk.Entry(frm, textvariable=self.b_var, width=6)
        self.b_entry.grid(row=0, column=9, padx=1, sticky="w")

        tk.Label(frm, text="X-O(Å):").grid(row=1, column=0, sticky="e")
        self.target_dist_var = tk.StringVar(value="2.77648")
        tk.Entry(frm, textvariable=self.target_dist_var, width=6).grid(row=1, column=1, padx=1, sticky="w")

        tk.Label(frm, text="nx:").grid(row=1, column=2, sticky="e")
        self.nx_var = tk.StringVar(value="3")
        tk.Entry(frm, textvariable=self.nx_var, width=6).grid(row=1, column=3, padx=1, sticky="w")

        tk.Label(frm, text="ny:").grid(row=1, column=4, sticky="e")
        self.ny_var = tk.StringVar(value="3")
        tk.Entry(frm, textvariable=self.ny_var, width=6).grid(row=1, column=5, padx=1, sticky="w")

        cb_frame = tk.Frame(frm)
        cb_frame.grid(row=2, column=0, columnspan=10, sticky="w", pady=5)
        tk.Checkbutton(cb_frame, text="启用 T 层", variable=self.enable_t_var, command=self.toggle_t_b).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(cb_frame, text="启用 B 层系", variable=self.enable_b_var, command=self.toggle_t_b).pack(side=tk.LEFT, padx=15)

        add_frame = tk.Frame(frm)
        add_frame.grid(row=3, column=0, columnspan=10, sticky="w", pady=2)

        tk.Label(add_frame, text="添加层:").pack(side=tk.LEFT)
        for m in ["XO", "XO2", "XO3", "M6", "M7"]:
            tk.Button(add_frame, text=m, width=5, command=lambda mode=m: self.add_layer(mode)).pack(side=tk.LEFT, padx=2)

        self.btn_x = tk.Button(add_frame, text="X", width=5, command=lambda: self.add_layer("X"))
        self.btn_x.pack(side=tk.LEFT, padx=2)
        self.btn_xbo3 = tk.Button(add_frame, text="XBO3", width=5, command=lambda: self.add_layer("XBO3"))
        self.btn_xbo3.pack(side=tk.LEFT, padx=2)
        self.btn_bo3 = tk.Button(add_frame, text="BO3", width=5, command=lambda: self.add_layer("BO3"))
        self.btn_bo3.pack(side=tk.LEFT, padx=2)
        self.btn_xb3o6 = tk.Button(add_frame, text="XB3O6", width=6, command=lambda: self.add_layer("XB3O6"))
        self.btn_xb3o6.pack(side=tk.LEFT, padx=2)

        tk.Button(add_frame, text="清除", width=5, command=self.clear_layers).pack(side=tk.LEFT, padx=6)

        tk.Label(frm, text="主层序列:").grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
        self.layers_var = tk.StringVar(value="")
        tk.Entry(frm, textvariable=self.layers_var, width=70).grid(row=4, column=2, columnspan=8, padx=2, sticky="w")

        tk.Label(frm, text="主层堆叠序:").grid(row=5, column=0, columnspan=2, sticky="w")
        self.stack_var = tk.StringVar(value="ABC")
        tk.Entry(frm, textvariable=self.stack_var, width=20).grid(row=5, column=2, columnspan=3, padx=2, sticky="w")

        tk.Checkbutton(frm, text="允许输出非电中性原胞", variable=self.allow_non_neutral_var, fg="darkred").grid(
            row=6, column=0, columnspan=6, sticky="w", pady=3
        )
        desc_text = (
            "说明：\n"
            "1. 平移参数 (angle:dx:dy) 中的 dx, dy 不再预先绑定固定网格。\n"
            "2. 主层(XB3O6/XBO3/XO3/XO2/XO/X/BO3)自动识别网格时优先只看 X 原子位置。\n"
            "3. M6层由 M7 层删除对应位置原子形成；且偏移量解释使用对应的 M7 网格。\n"
            "4. M7层网格由相邻主层的 X 原子网格决定。\n"
            "5. T层自动识别网格时只看 T 原子位置。\n"
            "6. XB3O6层使用特殊ABC平移：B->(7/(3nx),7/(3ny))，C->(14/(3nx),14/(3ny))。\n"
            "7. 当M层夹在XB3O6层之间时，M层也使用同样的特殊ABC平移。\n"
            "8. M层的堆叠标签由上下两层主层堆叠方式唯一确定：AB→C，BC→A，AC→B；若两侧相同则保持相同。\n"
            "9. 已取消翻转判定，XBO3/BO3 层固定默认 B 位。"
        )
        tk.Label(frm, text=desc_text, fg="blue", justify=tk.LEFT).grid(row=7, column=0, columnspan=10, sticky="w")

    def toggle_t_b(self):
        state_t = tk.NORMAL if self.enable_t_var.get() else tk.DISABLED
        self.t_entry.config(state=state_t)
        state_b = tk.NORMAL if self.enable_b_var.get() else tk.DISABLED
        self.b_entry.config(state=state_b)
        self.btn_x.config(state=state_b)
        self.btn_xbo3.config(state=state_b)
        self.btn_bo3.config(state=state_b)
        self.btn_xb3o6.config(state=state_b)

    def build_output_frame(self):
        frm = tk.Frame(self.root)
        frm.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.text_box = tk.Text(frm, wrap="word", height=24)
        self.text_box.pack(fill=tk.BOTH, expand=True)
        msg = (
            "程序就绪。\n\n"
            "【当前版本说明】\n"
            "本版本中 (angle:dx:dy) 的 dx, dy 均表示“该层自动识别出的局部网格步数”。\n"
            "其中：主层按 X 原子建网格，M6由 M7 删除对应位置原子形成，且偏移量解释使用对应的 M7 网格，M7按相邻主层X原子网格建网格，T层按 T 原子建网格。\n"
            "XB3O6层使用特殊ABC平移；夹在XB3O6层之间的M层也使用同样的特殊ABC平移。\n"
            "M层堆叠标签由相邻上下主层决定：AB→C，BC→A，AC→B；若两侧相同则保持相同。\n"
            "已取消翻转判定，XBO3/BO3 层固定默认 B 位。"
        )
        self.text_box.insert("1.0", msg)
        self.text_box.config(state="disabled")

    def build_button_frame(self):
        frm = tk.Frame(self.root)
        frm.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        ttk.Button(frm, text="1. 生成超胞结构", command=self.generate_structure).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        ttk.Button(frm, text="2. 保存超胞 CIF", command=self.save_cif).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        ttk.Button(frm, text="3. 对称性分析与原胞导出", command=self.analyze_and_export_primitive).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        ttk.Button(frm, text="4. 导出二维绘图", command=self.export_plot_2d).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        ttk.Button(frm, text="5. 导出原型档案", command=self.export_to_prototype_db).pack(side=tk.LEFT, expand=True,                                                                                      fill=tk.X, padx=4)
        ttk.Button(frm, text="6. X位点配位环境分析", command=self.analyze_x_coordination).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)
        ttk.Button(frm, text="退出", command=self.root.destroy).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=4)

    def update_output(self, message):
        # 1. 如果当前正在显示 3D 画布，先将其隐藏
        if hasattr(self, 'canvas_widget') and self.canvas_widget is not None:
            self.canvas_widget.pack_forget()
        # 2. 确保白色文本框处于显示状态
        if not self.text_box.winfo_ismapped():
            self.text_box.pack(fill=tk.BOTH, expand=True)
        # 3. 正常更新文本信息
        self.text_box.config(state="normal")
        self.text_box.delete("1.0", tk.END)
        self.text_box.insert("1.0", message)
        self.text_box.config(state="disabled")

    def clear_layers(self):
        self.layers_var.set("")

    def add_layer(self, mode):
        current = self.layers_var.get()
        self.layers_var.set(current + "," + mode if current else mode)

    def parse_layer_modes(self, text):
        raw_tokens = [x.strip() for x in text.split(",") if x.strip()]
        modes, alphas, angles, dxs, dys = [], [], [], [], []
        valid_modes = ["XO", "XO2", "XO3", "M6", "M7"]
        if self.enable_b_var.get():
            valid_modes.extend(["X", "XBO3", "BO3", "XB3O6"])

        current_main_idx = -1
        for token in raw_tokens:
            try:
                val = parse_number_or_fraction(token)
                if current_main_idx >= 0:
                    alphas[current_main_idx] = val
                    continue
                else:
                    raise ValueError("层间距系数(α)不能出现在第一个主层之前。")
            except ValueError:
                pass

            m_raw = token.strip()
            angle, dx, dy = 0.0, 0.0, 0.0

            if "(" in m_raw and m_raw.endswith(")"):
                idx = m_raw.index("(")
                m = m_raw[:idx].upper().strip()
                param_str = m_raw[idx + 1:-1]
                parts = param_str.split(":")
                if len(parts) > 0 and parts[0].strip():
                    angle = parse_number_or_fraction(parts[0])
                if len(parts) > 1 and parts[1].strip():
                    dx = parse_number_or_fraction(parts[1])
                if len(parts) > 2 and parts[2].strip():
                    dy = parse_number_or_fraction(parts[2])
            else:
                m = m_raw.upper()

            if m not in valid_modes:
                if m in ["X", "XBO3", "BO3", "XB3O6"] and not self.enable_b_var.get():
                    raise ValueError(f"层模式 '{m}' 被拒绝：当前 B 层系已被禁用。")
                raise ValueError(f"无效或未注册的层模式: {token}")

            modes.append(m)
            angles.append(angle)
            dxs.append(dx)
            dys.append(dy)

            if m in ["XO", "XO2", "XO3", "X", "XBO3", "BO3", "XB3O6"]:
                current_main_idx += 1
                alphas.append(1.0)

        return modes, alphas, angles, dxs, dys

    def generate_structure(self):
        try:
            layer_modes, layer_alphas, layer_angles, layer_dxs, layer_dys = self.parse_layer_modes(self.layers_var.get())

            gen = LayeredXOGenerator(
                x_element=self.x_var.get().strip(),
                o_element=self.o_var.get().strip(),
                m_element=self.m_var.get().strip(),
                t_element=self.t_var.get().strip(),
                b_element=self.b_var.get().strip(),
                target_xo_distance=float(self.target_dist_var.get()),
                nx=int(self.nx_var.get()),
                ny=int(self.ny_var.get()),
                enable_t=self.enable_t_var.get()
            )

            result = gen.build_structure(
                layer_modes, layer_alphas, self.stack_var.get().strip(),
                layer_angles, layer_dxs, layer_dys
            )

            self.structure = result[0]
            self._last_build = {"gen": gen, "result": result}

            info = gen.analyze_structure(self.structure)

            exact_flag = result[1]
            expanded_modes = result[6]
            expanded_angles = result[10]
            expanded_dxs = result[11]
            expanded_dys = result[12]
            ref_mode = result[13]

            layer_data = gen.get_layer_atoms_for_plot(
                result[6], result[7], result[8], result[10], result[11], result[12], result[2], result[0].lattice
            )

            display_seq = []
            for i, (m, ang, dx, dy) in enumerate(zip(expanded_modes, expanded_angles, expanded_dxs, expanded_dys)):
                gx = layer_data[i]["grid_x"]
                gy = layer_data[i]["grid_y"]
                if ang != 0.0 or dx != 0.0 or dy != 0.0:
                    display_seq.append(f"{m}({ang}:{dx}:{dy})[auto-grid={gx}x{gy}]")
                else:
                    display_seq.append(f"{m}[auto-grid={gx}x{gy}]")

            if exact_flag:
                lattice_msg = f"无晶格失配：面内基矢严格遵循单一同构层系 ({ref_mode}) 的本征参数。"
            else:
                lattice_msg = f"检测到异质构型层：宏观晶胞基矢已强制锁定为最高优先级骨架 ({ref_mode}) 的特征晶格，以建立共格界面。"

            try:
                sga = SpacegroupAnalyzer(self.structure, symprec=1e-3)
                prim_struct = sga.get_primitive_standard_structure()
                sg_symbol = sga.get_space_group_symbol()
                sg_number = sga.get_space_group_number()

                prim_sites_str = ""
                for site in prim_struct:
                    prim_sites_str += f"    {site.specie.symbol:<3}: ({site.frac_coords[0]:8.4f}, {site.frac_coords[1]:8.4f}, {site.frac_coords[2]:8.4f})\n"

                prim_info = (
                    f"空间群: {sg_symbol} (No. {sg_number})\n"
                    f"最小原胞参数: a={prim_struct.lattice.a:.4f}Å, b={prim_struct.lattice.b:.4f}Å, c={prim_struct.lattice.c:.4f}Å\n"
                    f"原胞原子分数坐标:\n{prim_sites_str}"
                )
            except Exception as sg_e:
                prim_info = f"无法自动提取原胞数据 (可能由于容差引起)。\n错误详情: {sg_e}"

            msg = [
                "结构生成成功",
                "=" * 60,
                f"最终层序列: {' | '.join(display_seq)}",
                f"超胞化学式: {info['formula']}",
                f"宏观标度锚定规则: {lattice_msg}",
                f"超胞绝对参数: a={info['a']:.5f}Å, b={info['b']:.5f}Å, c={info['c']:.5f}Å",
                "-" * 60,
                prim_info
            ]
            self.update_output("\n".join(msg))

        except Exception as e:
            messagebox.showerror("错误", f"生成结构失败：\n{e}")

    def save_cif(self):
        if self.structure is None:
            return
        filename = fd.asksaveasfilename(title="保存超胞 CIF", defaultextension=".cif", initialfile="supercell.cif")
        if filename:
            CifWriter(self.structure).write_file(filename)
            messagebox.showinfo("成功", f"CIF 已保存至：\n{filename}")

    def analyze_and_export_primitive(self):
        if self.structure is None:
            return
        try:
            symprec = 1e-3
            sga_supercell = SpacegroupAnalyzer(self.structure, symprec=symprec)
            primitive_structure = sga_supercell.get_primitive_standard_structure()

            comp = primitive_structure.composition
            reduced_formula = comp.reduced_formula
            is_neutral = len(comp.oxi_state_guesses()) > 0

            if not is_neutral and not self.allow_non_neutral_var.get():
                messagebox.showwarning("拦截", "化学式非电中性，原胞生成强制终止。")
                return

            filename = fd.asksaveasfilename(
                title="保存标准原胞 CIF",
                defaultextension=".cif",
                initialfile=f"primitive_{reduced_formula}.cif"
            )
            if not filename:
                return

            sga_primitive = SpacegroupAnalyzer(primitive_structure, symprec=symprec)
            primitive_lattice = primitive_structure.lattice
            lattice_info = (
                f"晶格参数: a={primitive_lattice.a:.4f}Å, b={primitive_lattice.b:.4f}Å, c={primitive_lattice.c:.4f}Å, "
                f"α={primitive_lattice.alpha:.2f}°, β={primitive_lattice.beta:.2f}°, γ={primitive_lattice.gamma:.2f}°"
            )

            symm_prim = sga_primitive.get_symmetrized_structure()
            unique_sites = [group[0] for group in symm_prim.equivalent_sites]
            primitive_sites = [
                f"    {site.specie.symbol:<3}: ({site.frac_coords[0]:8.4f}, {site.frac_coords[1]:8.4f}, {site.frac_coords[2]:8.4f})"
                for site in unique_sites
            ]

            msg = [
                "=== 晶体对称性报告 ===",
                f"原胞化学式: {reduced_formula}",
                f"电中性状态: {'满足' if is_neutral else '未满足 (强制输出)'}",
                f"空间群: {sga_primitive.get_space_group_symbol()} (No. {sga_primitive.get_space_group_number()})",
                lattice_info,
                f"原胞独立原子位置（分数坐标，共 {len(unique_sites)} 处）:",
            ] + primitive_sites

            CifWriter(primitive_structure, symprec=symprec).write_file(filename)
            self.update_output("\n".join(msg))
            messagebox.showinfo("成功", f"标准原胞 ({reduced_formula}) 已生成。")
        except Exception as e:
            messagebox.showerror("错误", f"分析异常：\n{e}")

    def export_plot_2d(self):
        if self.structure is None or not hasattr(self, "_last_build"):
            return
        filename = fd.asksaveasfilename(title="保存二维层投影", defaultextension=".png", initialfile="layers.png")
        if not filename:
            return
        try:
            gen, result = self._last_build["gen"], self._last_build["result"]

            layer_data = gen.get_layer_atoms_for_plot(
                result[6], result[7], result[8], result[10], result[11], result[12], result[2], result[0].lattice
            )

            n_layers = len(layer_data)
            ncols = 3
            nrows = int(np.ceil(n_layers / ncols))
            fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(15, 5 * nrows))
            axes_flat = [axes] if nrows == 1 and ncols == 1 else axes.flatten()

            color_map = {
                self.x_var.get().strip(): "purple",
                self.o_var.get().strip(): "red",
                self.m_var.get().strip(): "purple",
                self.t_var.get().strip(): "blue",
                self.b_var.get().strip(): "green"
            }
            size_map = {
                self.x_var.get().strip(): 150,
                self.o_var.get().strip(): 50,
                self.m_var.get().strip(): 80,
                self.t_var.get().strip(): 80,
                self.b_var.get().strip(): 50
            }

            for idx, layer in enumerate(layer_data):
                ax = axes_flat[idx]
                for elem, fx, fy in layer["atoms"]:
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            ax.scatter(
                                fx + dx, fy + dy,
                                s=size_map.get(elem, 70),
                                c=color_map.get(elem, "black"),
                                edgecolors="black",
                                linewidths=0.5,
                                alpha=0.85
                            )

                title = f"Layer {idx+1}: {layer['mode']} "
                if layer['theta'] != 0.0 or layer['dx'] != 0.0 or layer['dy'] != 0.0:
                    title += f"({layer['theta']}° : {layer['dx']} : {layer['dy']}) "
                title += f"| auto-grid={layer['grid_x']}x{layer['grid_y']} | z={layer['z']:.4f}"

                ax.set_title(title, fontsize=12, fontweight='bold')
                ax.set_aspect("equal")
                ax.set_xlim(-0.2, 1.2)
                ax.set_ylim(-0.2, 1.2)
                ax.grid(True, linestyle="--", alpha=0.3)

            for idx in range(n_layers, len(axes_flat)):
                axes_flat[idx].axis("off")

            fig.tight_layout()
            fig.savefig(filename, dpi=300, bbox_inches="tight")
            plt.close(fig)
            messagebox.showinfo("成功", "二维绘图已保存。")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败：\n{e}")

    def export_to_prototype_db(self):
        import json
        from tkinter import filedialog as fd
        from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
        from tkinter import messagebox

        if self.structure is None or not hasattr(self, "_last_build"):
            messagebox.showwarning("提示", "请先生成并检查一个结构！")
            return

        try:
            # 1. 从缓存中提取拓扑基因特征
            result = self._last_build["result"]
            expanded_modes = result[6]
            expanded_shifts = result[7]
            main_shift_sequence = result[9]
            ref_grid = result[13]

            # 2. 自动进行空间群与 Wyckoff 分析 (采用最稳妥的底层 dataset 提取法)
            sga = SpacegroupAnalyzer(self.structure, symprec=1e-3)
            dataset = sga.get_symmetry_dataset()

            wyckoff_sig = {}
            if dataset and "wyckoffs" in dataset:
                wyckoffs_list = dataset["wyckoffs"]
                # 直接遍历所有原子，wyckoffs_list 的长度和 structure 中的原子数绝对一致
                for idx, site in enumerate(self.structure):
                    elem = site.specie.symbol
                    w_letter = wyckoffs_list[idx]

                    if elem not in wyckoff_sig:
                        wyckoff_sig[elem] = set()  # 使用 set 自动去重
                    wyckoff_sig[elem].add(w_letter)

            # 3. 组装标准数据库文档 (双轨记录)
            prototype_id = f"{'-'.join(expanded_modes)}-{ref_grid}"
            doc = {
                "topology_theory": {
                    "prototype_id": prototype_id,
                    "input_main_shifts": main_shift_sequence,
                    "expanded_modes": expanded_modes,
                    "expanded_shifts": expanded_shifts,
                    "reference_grid": ref_grid
                },
                "prototype_crystallography": {
                    "ideal_space_group": sga.get_space_group_symbol(),
                    "space_group_number": sga.get_space_group_number(),
                    "crystal_system": sga.get_crystal_system(),
                    "is_neutral": len(self.structure.composition.oxi_state_guesses()) > 0,
                    "wyckoff_signature": {k: ", ".join(sorted(v)) for k, v in wyckoff_sig.items()}
                },
                "real_compounds": []
            }

            # 4. 弹窗保存
            filename = fd.asksaveasfilename(
                title="保存原型数据库档案",
                defaultextension=".json",
                initialfile=f"Proto_{prototype_id}.json"
            )

            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(doc, f, indent=4, ensure_ascii=False)

                msg = f"成功！结构原型档案已导出至：\n{filename}\n\n该结构已被标记为专家审核通过的可用原型。"
                self.update_output(msg)
                messagebox.showinfo("入库成功", "一键入库完成！")

        except Exception as e:
            messagebox.showerror("错误", f"导出数据库档案失败：\n{e}")

            # ... (上面是 export_to_prototype_db 的原有代码) ...
            if filename:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(doc, f, indent=4, ensure_ascii=False)

                msg = f"成功！结构原型档案已导出至：\n{filename}\n\n该结构已被标记为专家审核通过的可用原型。"
                self.update_output(msg)
                messagebox.showinfo("入库成功", "一键入库完成！")

        except Exception as e:
            messagebox.showerror("错误", f"导出数据库档案失败：\n{e}")

    def analyze_x_coordination(self):
        """分析堆垛结构中 X 位点周围的 O 配位环境，并在下方的白色框中直接显示三维可交互模型(支持鼠标悬停显距)"""
        if self.structure is None:
            import tkinter.messagebox as messagebox
            messagebox.showwarning("提示", "请先生成结构！")
            return

        try:
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from mpl_toolkits.mplot3d.art3d import Poly3DCollection
            from scipy.spatial import ConvexHull
            import matplotlib.pyplot as plt
            import numpy as np
            import tkinter as tk

            plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'Heiti TC', 'SimHei']
            plt.rcParams['axes.unicode_minus'] = False

            x_elem = self.x_var.get().strip()
            o_elem = self.o_var.get().strip()

            target_dist = float(self.target_dist_var.get())
            cutoff_radius = target_dist * 1.35

            x_sites = [site for site in self.structure if site.specie.symbol == x_elem]
            if not x_sites:
                messagebox.showerror("错误", f"结构中未找到 {x_elem} 原子！")
                return

            env_dict = {}
            for site in x_sites:
                neighbors = self.structure.get_neighbors(site, r=cutoff_radius)
                o_neighbors = [nn for nn in neighbors if nn.specie.symbol == o_elem]
                cn = len(o_neighbors)
                if cn > 0 and cn not in env_dict:
                    env_dict[cn] = (site, o_neighbors)

            if not env_dict:
                messagebox.showinfo("提示", f"未在 {cutoff_radius:.2f} Å 范围内找到配位氧原子。")
                return

            unique_cns = sorted(list(env_dict.keys()))
            num_plots = len(unique_cns)

            fig = Figure(figsize=(6 * num_plots, 6), dpi=100, facecolor='#F5F5F7')


            # 用于存储每个子图的交互数据
            interactive_data = []

            for idx, cn in enumerate(unique_cns):
                center_site, o_neighbors = env_dict[cn]

                ax = fig.add_subplot(1, num_plots, idx + 1, projection='3d')
                ax.set_facecolor('#F5F5F7')

                ax.scatter([0], [0], [0], color='#9400D3', s=600, label=f'{x_elem} (中心)',
                           edgecolors='white', linewidths=2, zorder=5, depthshade=True)

                ox, oy, oz, lengths = [], [], [], []
                for nn in o_neighbors:
                    dx = nn.coords[0] - center_site.coords[0]
                    dy = nn.coords[1] - center_site.coords[1]
                    dz = nn.coords[2] - center_site.coords[2]
                    ox.append(dx)
                    oy.append(dy)
                    oz.append(dz)
                    # 计算该键的真实物理长度
                    lengths.append(np.linalg.norm([dx, dy, dz]))

                    ax.plot([0, dx], [0, dy], [0, dz], color='#B0C4DE', linestyle='-', linewidth=3.5, alpha=0.8,
                            zorder=1)

                # 绘制氧原子，并保存 scatter 对象以便后续捕捉鼠标事件
                sc = ax.scatter(ox, oy, oz, color='#FF4500', s=250, label=f'O (CN={cn})',
                                edgecolors='white', linewidths=1.5, zorder=6, depthshade=True)

                points = np.column_stack((ox, oy, oz))
                if len(points) >= 4:
                    try:
                        hull = ConvexHull(points)
                        faces = [points[simplex] for simplex in hull.simplices]
                        poly3d = Poly3DCollection(faces, facecolors='#00CED1', linewidths=1.5,
                                                  edgecolors='#008B8B', alpha=0.25, zorder=2)
                        ax.add_collection3d(poly3d)
                    except Exception as e:
                        pass

                ax.set_title(f"{x_elem} 原子的 {cn} 配位环境", fontsize=16, fontweight='bold', pad=10, color='#333333')
                ax.legend(loc='lower right', fontsize=11, framealpha=0.8, edgecolor='#DDDDDD')

                # 创建一个隐藏的文本框，用于悬停时显示键长 (放在左上角)
                hover_text = ax.text2D(0.05, 0.95, "", transform=ax.transAxes, fontsize=13, color='darkred',
                                       fontweight='bold',
                                       bbox=dict(boxstyle="round,pad=0.3", fc="#FFFFE0", ec="#FFD700", alpha=0.9),
                                       zorder=10)

                # 设置真实比例
                ax.set_box_aspect([1, 1, 1])

                max_range = np.array([max(ox) - min(ox), max(oy) - min(oy), max(oz) - min(oz)]).max() / 2.0
                mid_x = (max(ox) + min(ox)) * 0.5
                mid_y = (max(oy) + min(oy)) * 0.5
                mid_z = (max(oz) + min(oz)) * 0.5
                ax.set_xlim(mid_x - max_range, mid_x + max_range)
                ax.set_ylim(mid_y - max_range, mid_y + max_range)
                ax.set_zlim(mid_z - max_range, mid_z + max_range)

                # 记录该子图的交互信息
                interactive_data.append({'ax': ax, 'sc': sc, 'lengths': lengths, 'hover_text': hover_text})

            self.text_box.pack_forget()

            if hasattr(self, 'canvas_widget') and self.canvas_widget is not None:
                self.canvas_widget.destroy()

            parent_frame = self.text_box.master
            canvas = FigureCanvasTkAgg(fig, master=parent_frame)
            self.canvas_widget = canvas.get_tk_widget()
            self.canvas_widget.pack(fill=tk.BOTH, expand=True)

            # ==========================================
            # 鼠标悬停事件的监听与处理逻辑
            # ==========================================
            def on_hover(event):
                changed = False
                for data in interactive_data:
                    # 检查鼠标是否在这个子图内
                    if event.inaxes == data['ax']:
                        # 检查鼠标是否碰到了某个氧原子
                        cont, ind = data['sc'].contains(event)
                        if cont:
                            # 获取被碰到的原子索引
                            idx = ind["ind"][0]
                            bond_len = data['lengths'][idx]
                            # 更新提示框文本
                            data['hover_text'].set_text(f"🎯 选定键长: {bond_len:.4f} Å")
                            changed = True
                        else:
                            # 鼠标移开时清空提示框
                            if data['hover_text'].get_text() != "":
                                data['hover_text'].set_text("")
                                changed = True

                # 只有状态发生改变时才重新绘制，避免卡顿
                if changed:
                    canvas.draw_idle()

            # 将悬停事件绑定到画布上
            canvas.mpl_connect("motion_notify_event", on_hover)

            canvas.draw()

        except Exception as e:
            import tkinter.messagebox as messagebox
            messagebox.showerror("可视化错误", f"生成 3D 视图时发生异常:\n{e}")

if __name__ == "__main__":
    XOApp()