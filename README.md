# TMC 主题美术工坊

同一个仓库，两个可单独安装、独立运行的 Codex 插件。

| 阶段 | 插件 | 输入 | 输出 |
| --- | --- | --- | --- |
| Stage 1 · 场景候选 | [theme-scene-studio](plugins/theme-scene-studio/) | 主题清单，可选 1–3 张参考图 | 每个主题 3 张候选图及生成记录 |
| Stage 2 · 背景与素材 | [theme-stage2](plugins/theme-stage2/) | 一张选定的场景图 | 1 张背景 + 12–15 个独立素材 PNG，默认 14 个 |

两个阶段仅通过场景图片衔接。Stage 2 不导入 Stage 1 代码，不读取它的 manifest，不要求安装或运行 Stage 1；用户直接提供成品场景图也能使用。两个插件不会互相触发。


**完整流程：主题 → 布局 agent 设计并审核 A/B/C 草图 → Stage 1 的 A/B/C 候选 → 选定一张图片 → Stage 2 的背景与素材 PNG。**

- 想探索不同主题和布局：使用 Stage 1。
- 已经有完整场景图，想制作独立背景和物件：直接使用 Stage 2。
- 两个插件各自有入口、版本、资源和运行目录，可以只安装其中一个。

[看 Stage 1 案例](#stage1-case) · [看 Stage 2 案例](#stage2-cases) · [安装](#安装) · [分阶段使用](#使用)

<a name="stage1-case"></a>

## Case · Stage 1：河畔村落 → 威尼斯水城

参考图提供美术风格，主题决定地形、建筑和布局；同一主题独立生成 A/B/C 三种候选。

<p align="center"><a href="plugins/theme-scene-studio/docs/examples/venice/reference.png"><img src="plugins/theme-scene-studio/docs/examples/venice/reference.png" width="360" alt="Stage 1 输入：河畔村落参考图"></a><br>输入 · 河畔村落参考图</p>

<table>
<tr><th width="33%">A · 两岸均衡</th><th width="33%">B · 中心广场</th><th width="33%">C · 沿岸串联</th></tr>
<tr>
<td><a href="plugins/theme-scene-studio/docs/examples/venice/candidate-a.png"><img src="plugins/theme-scene-studio/docs/examples/venice/candidate-a.png" width="100%" alt="威尼斯候选A"></a></td>
<td><a href="plugins/theme-scene-studio/docs/examples/venice/candidate-b.png"><img src="plugins/theme-scene-studio/docs/examples/venice/candidate-b.png" width="100%" alt="威尼斯候选B"></a></td>
<td><a href="plugins/theme-scene-studio/docs/examples/venice/candidate-c.png"><img src="plugins/theme-scene-studio/docs/examples/venice/candidate-c.png" width="100%" alt="威尼斯候选C"></a></td>
</tr>
</table>

[查看案例来源与已知问题](plugins/theme-scene-studio/docs/examples/venice/README.md)。三张图用于方向选择，尚非经过玩法验证的关卡。

<a name="stage2-cases"></a>

## Case · Stage 2：完整场景 → 背景 + 独立素材

下面是两个独立主题的真实运行案例，与上面的威尼斯案例分别展示两个阶段的能力。Stage 2 会依据源图识别物件并重新生成，不是简单裁图，也不会自动把素材回拼成关卡。

正式版背景采用适中细节和柔和体积，保留树木、水流与必要地形结构；物件采用 V2 的邻近色描边、可读体积与卡通夸张。下列图片均来自已保存结果，没有为文档重新生成。

### 东方水墨仙境

<table>
<tr><th width="50%">输入整图</th><th width="50%">独立背景</th></tr>
<tr><td><a href="docs/examples/stage2/ink-fantasy/input.png"><img src="docs/examples/stage2/ink-fantasy/input.png" width="100%" alt="东方水墨仙境输入整图"></a></td><td><a href="docs/examples/stage2/ink-fantasy/background.png"><img src="docs/examples/stage2/ink-fantasy/background.png" width="100%" alt="东方水墨仙境独立背景"></a></td></tr>
</table>

独立素材节选（6 / 14，均为透明 PNG）：

<table>
<tr>
<td width="33%" align="center"><a href="docs/examples/stage2/ink-fantasy/assets/building-01.png"><img src="docs/examples/stage2/ink-fantasy/assets/building-01.png" height="150" alt="竹屋透明素材"></a><br>竹屋</td>
<td width="33%" align="center"><a href="docs/examples/stage2/ink-fantasy/assets/vehicle-01.png"><img src="docs/examples/stage2/ink-fantasy/assets/vehicle-01.png" height="150" alt="竹筏透明素材"></a><br>竹筏</td>
<td width="33%" align="center"><a href="docs/examples/stage2/ink-fantasy/assets/vehicle-03.png"><img src="docs/examples/stage2/ink-fantasy/assets/vehicle-03.png" height="150" alt="仙鹤坐骑透明素材"></a><br>仙鹤坐骑</td>
</tr>
<tr>
<td width="33%" align="center"><a href="docs/examples/stage2/ink-fantasy/assets/facility-01.png"><img src="docs/examples/stage2/ink-fantasy/assets/facility-01.png" height="150" alt="石灯笼透明素材"></a><br>石灯笼</td>
<td width="33%" align="center"><a href="docs/examples/stage2/ink-fantasy/assets/facility-03.png"><img src="docs/examples/stage2/ink-fantasy/assets/facility-03.png" height="150" alt="石茶桌透明素材"></a><br>石茶桌</td>
<td width="33%" align="center"><a href="docs/examples/stage2/ink-fantasy/assets/character-03.png"><img src="docs/examples/stage2/ink-fantasy/assets/character-03.png" height="150" alt="琴师鹅透明素材"></a><br>琴师鹅</td>
</tr>
</table>

[查看全部 14 个素材与复核说明](docs/examples/stage2/ink-fantasy/README.md)。本组 11 个素材通过复核，3 个待微调；首页展示其中已通过的 6 个。

### 沙漠绿洲集市

<table>
<tr><th width="50%">输入整图</th><th width="50%">独立背景</th></tr>
<tr><td><a href="docs/examples/stage2/desert-oasis/input.png"><img src="docs/examples/stage2/desert-oasis/input.png" width="100%" alt="沙漠绿洲集市输入整图"></a></td><td><a href="docs/examples/stage2/desert-oasis/background.png"><img src="docs/examples/stage2/desert-oasis/background.png" width="100%" alt="沙漠绿洲集市独立背景"></a></td></tr>
</table>

独立素材节选（6 / 14，均为透明 PNG）：

<table>
<tr>
<td width="33%" align="center"><a href="docs/examples/stage2/desert-oasis/assets/building-01.png"><img src="docs/examples/stage2/desert-oasis/assets/building-01.png" height="150" alt="平顶土屋透明素材"></a><br>平顶土屋</td>
<td width="33%" align="center"><a href="docs/examples/stage2/desert-oasis/assets/building-04.png"><img src="docs/examples/stage2/desert-oasis/assets/building-04.png" height="150" alt="橙篷商铺透明素材"></a><br>橙篷商铺</td>
<td width="33%" align="center"><a href="docs/examples/stage2/desert-oasis/assets/vehicle-01.png"><img src="docs/examples/stage2/desert-oasis/assets/vehicle-01.png" height="150" alt="绿洲帆船透明素材"></a><br>绿洲帆船</td>
</tr>
<tr>
<td width="33%" align="center"><a href="docs/examples/stage2/desert-oasis/assets/vehicle-02.png"><img src="docs/examples/stage2/desert-oasis/assets/vehicle-02.png" height="150" alt="载货骆驼透明素材"></a><br>载货骆驼</td>
<td width="33%" align="center"><a href="docs/examples/stage2/desert-oasis/assets/facility-02.png"><img src="docs/examples/stage2/desert-oasis/assets/facility-02.png" height="150" alt="棕榈树透明素材"></a><br>棕榈树</td>
<td width="33%" align="center"><a href="docs/examples/stage2/desert-oasis/assets/character-01.png"><img src="docs/examples/stage2/desert-oasis/assets/character-01.png" height="150" alt="头巾商人鹅透明素材"></a><br>头巾商人鹅</td>
</tr>
</table>

[查看全部 14 个素材与复核说明](docs/examples/stage2/desert-oasis/README.md)。本组 10 个素材通过复核，4 个待微调；首页展示其中已通过的 6 个。

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

### 1. 生成场景候选

每个主题先设计并审核三张布局草图，再输出三张场景候选；点击区占主体，非点击环境占少量。每张成品使用对应草图作为空间参考。未附图时使用 Stage 1 自带参考图。

```text
使用 $theme-scene-studio，生成威尼斯水城主题的三张候选图。
```

### 2. 选一张图，单独启动 Stage 2

把选定的 A、B 或 C 原始图片附到新任务中，再输入；也可直接提供已有的完整场景图，无需先运行 Stage 1：

```text
使用 $theme-stage2，处理这张场景图，输出独立背景和默认14个素材 PNG。
```

### 3. 获取独立 PNG

Stage 2 默认选择 14 个不同原型，通常为建筑 4、载具 3、设施 4、角色 3，按源图实际内容调整至 12–15 个。每个对象独立生成，背景另外生成；内部保留调用与复核记录，默认交付只有 PNG。缺少源图时会要求补充。

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
docs/examples/stage2/             # 两组真实输入、背景、透明素材与案例说明
tests/                            # 分发结构、独立运行及回归检查
```

[Stage 1 案例与完整说明](plugins/theme-scene-studio/README.md) · [Stage 2 完整说明](plugins/theme-stage2/README.md) · [阶段边界](docs/architecture.md)

## 验证

安装 Stage 2 的 Python 依赖后，在仓库根目录执行：

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s plugins/theme-stage2/runtime/tests -v
```

测试使用合成图像验证处理流程，不生成新美术素材，也不把测试通过当作美术通过。除明确选入 `docs/examples/` 的展示案例外，运行输出、个人缓存、凭证和批量任务记录不随仓库发布。
