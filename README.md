# TMC 主题美术工坊

同一个仓库，两个可单独安装、独立运行的 Codex 插件。

| 阶段 | 插件 | 输入 | 输出 |
| --- | --- | --- | --- |
| Stage 1 · 场景候选 | [theme-scene-studio](plugins/theme-scene-studio/) | 主题清单，可选 1–3 张参考图 | 每个主题 3 张候选图及生成记录 |
| Stage 2 · 背景与素材 | [theme-stage2](plugins/theme-stage2/) | 一张选定的场景图 | 1 张背景 + 12–15 个独立素材 PNG，默认 14 个 |

两个阶段仅通过场景图片衔接。Stage 2 不导入 Stage 1 代码，不读取它的 manifest，不要求安装或运行 Stage 1；用户直接提供成品场景图也能使用。两个插件不会互相触发。

## 安装

```bash
git clone https://github.com/WitMani/tmc-theme-scene-plugin.git
codex plugin marketplace add ./tmc-theme-scene-plugin

# 根据需要选装其中一个，或分别安装两个
codex plugin add theme-scene-studio@tmc-theme-scene
codex plugin add theme-stage2@tmc-theme-scene
```

仓库市场定义位于 [.agents/plugins/marketplace.json](.agents/plugins/marketplace.json)。安装完成后在新任务中使用对应技能。

原先根目录的 Stage 1 插件已迁移至 `plugins/theme-scene-studio/`；调用名 `$theme-scene-studio` 保持不变。旧安装不会自动变成双阶段插件，更新时按上面的市场入口选装；若原插件来自其他市场，请在切换来源时移除旧安装以避免重复技能。

## 使用

Stage 1：

```text
使用 $theme-scene-studio，生成威尼斯水城主题的三张候选图。
```

Stage 2：附上一张选定的场景图，再输入：

```text
使用 $theme-stage2，处理这张场景图，输出独立背景和默认14个素材 PNG。
```

Stage 2 正式版采用美术规则 **1.4.0**：背景的细节密度与体积感同时适度收敛，保留树木、水流、岸线和桥体；素材沿用 **V2** 的邻近色描边、克制但可读的体积和卡通夸张。V3 单次试验的反面参考与加强 Prompt 不作为默认输入。

生成依赖 Codex 内置图像工具。Stage 2 的本地透明化与检查还需要 Python 3.10+、Pillow、NumPy 和 SciPy：

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r plugins/theme-stage2/requirements.txt
python3 plugins/theme-stage2/scripts/run.py doctor
```

命令行只负责规划、留档、透明化、复核和导出，不会调用图像生成 API。透明 PNG 检查通过不代表美术验收通过；验收依然需要逐项观察。

## 目录

```text
.agents/plugins/marketplace.json    # 两个独立安装入口
plugins/
├── theme-scene-studio/            # Stage 1 插件、技能、默认参考图与案例
└── theme-stage2/                  # Stage 2 插件、技能、runtime、规范和测试
docs/architecture.md              # 阶段边界与迁移说明
tests/                            # 分发结构、独立运行及回归检查
```

[Stage 1 案例与完整说明](plugins/theme-scene-studio/README.md) · [Stage 2 完整说明](plugins/theme-stage2/README.md) · [阶段边界](docs/architecture.md)

## 验证

安装 Stage 2 的 Python 依赖后，在仓库根目录执行：

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s plugins/theme-stage2/runtime/tests -v
```

测试使用合成图像验证处理流程，不生成新美术素材，也不把测试通过当作美术通过。运行输出、个人缓存、凭证和本次批量出图记录不随仓库发布。
