# 三候选设计

同一主题的三张都使用同一参考组、最终C三项优化、同一主题清单、同一画幅和可比角色尺度。候选变化主要发生在空间布局和建筑群组织。候选方案是可按主题调整的设计建议，不硬编码河流或某种地形。

- **A — 均衡分布**：多个规模相近的建筑群与清晰的连接通路；均匀分配主题元素。
- **B — 局部聚集**：一个适度聚集的活动区与周边建筑群，留出通路；不让地标变为巨大主体。
- **C — 分区串联**：几个可辨识的小区域沿主题适用的通路串联，让留白和建筑群产生不同节奏。

生成前为当前主题写出真正不同的布局描述。例如威尼斯：A可为曲折运河两岸群落，B为围绕广场的几块岛状街区，C为连续岸线与几条支渠。月球：A为散布在浅陨石坑间的基地，B为中央工作区与周围舱群，C为串联数个小营区的月球车道路；不能机械套用水城运河。

英文差异段模板：

```text
CANDIDATE [A / B / C]
Keep the same theme vocabulary, reference-derived art style, color-aware outlines, light chromatic palette, restrained material response, framing and relative object scale as the other candidates.
For this candidate, organize the world as follows: [specific spatial design].
Make the arrangement meaningfully different through parcel shapes, cluster positions and circulation, while keeping a comparable detail budget and no oversized centerpiece.
Produce one standalone finished scene, not a contact sheet or a multi-panel image.
```

## 完成定义与异常

T个选定主题对应3T个槽位，参考组N张（1≤N≤3）不乘入数量。状态分别记录pending/generated/reviewed/failed等，明确状态含义。只有图片文件真实存在且查看过才可标记已检查。若A/B/C出现重复、严重画风漂移或工具失败，对该槽位最多额外尝试一次，保留历史。只有完成了全部槽位才报告全部完成。

在宣称“不同候选”时给出实际观察到的差异；不能仅因prompt不同就宣称图不同。检查结论是目视结论，不保证像素锁定、统一随机种子或可玩性。
