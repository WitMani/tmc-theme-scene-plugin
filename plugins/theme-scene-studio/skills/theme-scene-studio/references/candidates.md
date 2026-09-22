# 三候选设计

同一主题的三张都使用同一完整干净参考组及同一主图辅助线版、最终C三项优化、同一主题清单、同一画幅、同一斜俯视正交镜头朝向与俯角和可比角色尺度；鹅角色保持同一胖头鹅比例。候选变化主要发生在空间布局和建筑群组织。候选方案是可按主题调整的设计建议，不硬编码河流或某种地形。

- **A — 均衡分布**：多个规模相近的建筑群与清晰的连接通路；均匀分配主题元素。
- **B — 局部聚集**：一个适度聚集的活动区与周边建筑群，留出通路；不让地标变为巨大主体。
- **C — 分区串联**：几个可辨识的小区域沿主题适用的通路串联，让留白和建筑群产生不同节奏。

A/B/C都必须保持点击区占主体、非点击环境区占少量。每个空间方案先说明宽裕的点击物摆放区在哪里，再说明少量环境地形如何交代主题；不要通过增加非点击地形面积制造候选差异。

生成前为当前主题写出真正不同的布局描述。例如威尼斯：A可为曲折运河两岸群落，B为围绕广场的几块岛状街区，C为连续岸线与几条支渠。月球：A为散布在浅陨石坑间的基地，B为中央工作区与周围舱群，C为串联数个小营区的月球车道路；不能机械套用水城运河。

正交几何不要求规则网格。保持参考密度与少量主题环境点缀，避免通过大块空白制造差异；候选应改变聚落/地形/道路关系，而不是只微调同一排屋。

按 [场景生活逻辑](scene-life-logic.md) 同时控制单张内及候选间的设施重复：港口、水陆接驳、路网和跨越点随各自地形与用途组织，不把同一组港口＋道路＋桥梁复制到多个区域或三个候选中。合理的标准设施与素材实例复用保留。

生图前按 [layout-sketch.md](layout-sketch.md) 分别完成并审核 A/B/C 草图；每个成品只使用对应草图。

英文差异段模板：

```text
CANDIDATE [A / B / C]
Keep the same theme vocabulary, reference-derived art style, color-aware outlines, light chromatic palette, restrained material response, framing, fixed elevated orthographic camera orientation and elevation angle, and relative object scale as the other candidates. If characters are geese, reuse the same chubby big-round-headed goose proportions. Do not rotate or tilt the camera to create a variant.
For this candidate, organize the world as follows: [specific spatial design, identifying generous clickable placement zones and limited non-clickable environmental accents].
Make the arrangement meaningfully different through parcel shapes, cluster positions and circulation, while keeping a comparable detail budget and no oversized centerpiece.
Produce one standalone finished scene, not a contact sheet or a multi-panel image.
```

## 完成定义与异常

T个选定主题对应3T个槽位，干净原图N张（1≤N≤3，未输入时使用内置默认图一张），默认额外加入1张辅助线版，再加当前候选已审核布局草图1张，实际输入N+2张；草图与辅助线准备不计入候选数量，参考图数量不乘入数量。状态分别记录pending/generated/reviewed/failed等，明确状态含义。只有图片文件真实存在且查看过才可标记已检查。若A/B/C出现重复、严重画风漂移或工具失败，对该槽位最多额外尝试一次，保留历史。只有完成了全部槽位才报告全部完成。

在宣称“不同候选”时给出实际观察到的差异；不能仅因prompt不同就宣称图不同。检查结论是目视结论，不保证像素锁定、统一随机种子或可玩性。
