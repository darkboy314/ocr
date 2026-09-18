#!/usr/bin/env sh

set -eu

# 切换到脚本所在目录，避免从其他目录执行时找不到 pyproject.toml
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$PROJECT_DIR"

echo "项目目录: $PROJECT_DIR"

# 将常见的 uv 安装目录加入 PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# 检查 curl 或 wget
if ! command -v curl >/dev/null 2>&1 && \
   ! command -v wget >/dev/null 2>&1; then
    echo "错误：系统中没有 curl 或 wget，无法自动安装 uv"
    exit 1
fi

# 检查 uv 是否已经安装
if command -v uv >/dev/null 2>&1; then
    echo "检测到 uv: $(command -v uv)"
else
    echo "未检测到 uv，开始自动安装..."

    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        wget -qO- https://astral.sh/uv/install.sh | sh
    fi

    # 安装程序完成后重新加入 PATH
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

    if ! command -v uv >/dev/null 2>&1; then
        echo "错误：uv 安装完成，但当前 shell 找不到 uv"
        echo "请重新打开终端后再执行此脚本"
        exit 1
    fi

    echo "uv 安装成功"
fi

echo "uv 版本: $(uv --version)"

# 检查项目配置文件
if [ ! -f "pyproject.toml" ]; then
    echo "错误：当前目录没有 pyproject.toml"
    echo "当前目录: $PROJECT_DIR"
    exit 1
fi

# 同步项目依赖
echo
echo "开始执行 uv sync..."

if [ -f "uv.lock" ]; then
    # 有锁文件时，严格按照锁文件同步
    uv sync --locked
else
    # 没有锁文件时，解析并生成锁文件
    uv sync
fi

# 检查入口文件
if [ ! -f "src/main.py" ]; then
    echo "错误：找不到 src/main.py"
    exit 1
fi

# 使用 uv run 在项目虚拟环境中运行程序
echo
echo "开始运行 src/main.py..."
uv run python src/main.py