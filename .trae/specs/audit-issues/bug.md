# 已修复的 Bug

## Bug 1: `sympy.core` 模块缺失

- **错误**: `ModuleNotFoundError: No module named 'sympy.core'`
- **根因**: 虚拟环境中 `sympy` 包安装损坏，`sympy.core` 子目录完全缺失
- **修复**: 卸载后重新安装 `sympy==1.14.0`
  ```bash
  pip uninstall sympy -y
  pip install --force-reinstall --no-deps sympy==1.14.0
  ```

## Bug 2: torch 与 torchvision 版本不兼容

- **错误**: `RuntimeError: operator torchvision::nms does not exist` → 级联导致 `ModuleNotFoundError: Could not import module 'PreTrainedModel'`
- **根因**: `torch==2.13.0+cpu`（全局安装）与 `torchvision==0.28.0+cu126`（venv 安装，CUDA 版）不兼容，且来自不同构建源
- **修复**: 从 PyTorch 官方 CPU 索引重新安装 torchvision
  ```bash
  pip install torchvision --index-url https://download.pytorch.org/whl/cpu
  ```
  - 安装后: `torch==2.13.0+cpu` + `torchvision==0.28.0+cpu` ✓
