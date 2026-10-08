# 数量驱动面积规划

先固定本次原型、实例数、target/distractor角色、4096画幅与H130尺寸。目标数是总数子集。用户明确数量覆盖默认216；不继承高密度参考图的铺满构图。

草图前运行：

```bash
python3 "$SKILL_DIR/scripts/placement_area.py" --plan "$SCENE_PLAN" --out "$RUN/placement-area.json"
```

脚本以逐原型target_wh_px的屏幕包围盒作为保守占地包络估计。每件分配包络 `(w+g)*(h+g)`，乘实例数；默认g为该原型最长边20%，可用placement_gap_px明确覆盖并在density.basis解释。按placement_area_zone分组（只能选assets.zones中的地形；单一zone自动选择），每组加默认25%调整余量，再加独立规划的通行面积。比例是可调整设计初值，不是经验测得最优密度或像素地面面积。

可选scene-plan.placement_area_options包含reserve_ratio和route_area_px2（按zone的面积字典）。通路不能重复计入余量；运动航道宽度、长度与连接另写delivery_policy.route_plan，route_area_px2为局部通行预留；远海/边缘航道的延续不意味着整个海洋都是摆放容量。没有路线数值时默认0，执行者仍须说明无独立面积或补填路线预算，不能省略必要运动空间。

按报告反推合适的地块轮廓并在草图检查最小宽度、地形适用性、连通和遮挡。不要直接把屏幕矩形当世界地面尺寸。面积预算是构图目标而非严格像素mask；A/B/C形状可变但沿用同一尺度和需求。超画布时返回over_canvas_budget，禁止将数值钳制为100%而隐藏不足，或静默减量/缩小物件。

小数量收缩可用地形，允许安静环境占整图多数。大数量扩大适用地块，移走阻碍环境；不能只计算总量，忽略大建筑与角色占地差异。目标与干扰物都计入，水陆分别规划。

报告与scene-plan一并交付，在density.basis引用报告文件与假设。总量≤30的显式案例要求目视逐原型计数，无新增可数装饰；不精确时如实标记并按现有单槽位重试预算修正。面积规划与目视数量检查均不能代替Stage 2的PNG测量或Layout的mask/容量验证。
