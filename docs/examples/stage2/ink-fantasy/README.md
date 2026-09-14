# Stage 2 案例 · 东方水墨仙境

[返回仓库首页](../../../../README.md) · [Stage 2 使用说明](../../../../plugins/theme-stage2/README.md)

本例使用 2026-09-14 已保存的正式规则运行结果：美术配置 1.4.0，背景为最新平衡版，物件沿用 V2 逻辑。配图直接复制原文件，没有为 README 重新生成。

<table>
<tr><th width="50%">输入 · 完整场景</th><th width="50%">输出 · 独立背景</th></tr>
<tr><td><a href="input.png"><img src="input.png" width="100%" alt="东方水墨仙境输入整图"></a></td><td><a href="background.png"><img src="background.png" width="100%" alt="东方水墨仙境独立背景"></a></td></tr>
</table>

背景移除建筑、人物、载具和独立设施，保留树木、水流、岸线及桥体或码头，并收敛内部细节与明暗。它是生成式重建，不是从原图直接擦除后的像素级复原。

## 全部 14 个独立素材

每张图对应一次独立对象生成，图片本身含真实 alpha；页面只负责排版，没有把素材回拼成场景。点击可查看原 PNG。

### 建筑

<table>
<tr><th width="25%">竹屋</th><th width="25%">山间凉亭</th><th width="25%">双层寺庙</th><th width="25%">山村集市棚</th></tr>
<tr><td align="center"><a href="assets/building-01.png"><img src="assets/building-01.png" height="180" alt="竹屋透明PNG"></a></td><td align="center"><a href="assets/building-02.png"><img src="assets/building-02.png" height="180" alt="山间凉亭透明PNG"></a></td><td align="center"><a href="assets/building-03.png"><img src="assets/building-03.png" height="180" alt="双层寺庙透明PNG"></a></td><td align="center"><a href="assets/building-04.png"><img src="assets/building-04.png" height="180" alt="山村集市棚透明PNG"></a></td></tr>
<tr><td align="center">复核通过</td><td align="center">复核通过</td><td align="center">待调：材质 / 高光</td><td align="center">待调：材质 / 高光</td></tr>
</table>

### 载具

<table>
<tr><th width="33%">竹筏</th><th width="33%">篷船</th><th width="33%">仙鹤坐骑</th></tr>
<tr><td align="center"><a href="assets/vehicle-01.png"><img src="assets/vehicle-01.png" height="180" alt="竹筏透明PNG"></a></td><td align="center"><a href="assets/vehicle-02.png"><img src="assets/vehicle-02.png" height="180" alt="篷船透明PNG"></a></td><td align="center"><a href="assets/vehicle-03.png"><img src="assets/vehicle-03.png" height="180" alt="仙鹤坐骑透明PNG"></a></td></tr>
<tr><td align="center">复核通过</td><td align="center">复核通过</td><td align="center">复核通过</td></tr>
</table>

### 设施

<table>
<tr><th width="25%">石灯笼</th><th width="25%">石狮</th><th width="25%">石茶桌</th><th width="25%">竹长椅</th></tr>
<tr><td align="center"><a href="assets/facility-01.png"><img src="assets/facility-01.png" height="180" alt="石灯笼透明PNG"></a></td><td align="center"><a href="assets/facility-02.png"><img src="assets/facility-02.png" height="180" alt="石狮透明PNG"></a></td><td align="center"><a href="assets/facility-03.png"><img src="assets/facility-03.png" height="180" alt="石茶桌透明PNG"></a></td><td align="center"><a href="assets/facility-04.png"><img src="assets/facility-04.png" height="180" alt="竹长椅透明PNG"></a></td></tr>
<tr><td align="center">复核通过</td><td align="center">复核通过</td><td align="center">复核通过</td><td align="center">复核通过</td></tr>
</table>

### 角色

<table>
<tr><th width="33%">斗笠船夫鹅</th><th width="33%">僧侣鹅</th><th width="33%">琴师鹅</th></tr>
<tr><td align="center"><a href="assets/character-01.png"><img src="assets/character-01.png" height="180" alt="斗笠船夫鹅透明PNG"></a></td><td align="center"><a href="assets/character-02.png"><img src="assets/character-02.png" height="180" alt="僧侣鹅透明PNG"></a></td><td align="center"><a href="assets/character-03.png"><img src="assets/character-03.png" height="180" alt="琴师鹅透明PNG"></a></td></tr>
<tr><td align="center">复核通过</td><td align="center">待调：头身比例</td><td align="center">复核通过</td></tr>
</table>

## 复核说明

背景复核通过；14 个素材中 11 个通过，3 个仍需微调。正式版表示采用当前正式规则，不代表所有生成候选都自动验收合格。

- 双层寺庙：金饰高光偏亮。
- 山村集市棚：陶罐改成宽面但仍有矩形反光块，蔬菜更概括。
- 僧侣鹅：头颈仍偏长，未完全达到短颈两头身目标。

文件对应关系、SHA-256 和复核状态保存在 [case.json](case.json)。示例只用于理解输入与输出，不是插件默认输入，也不是可玩关卡或完整素材库。
