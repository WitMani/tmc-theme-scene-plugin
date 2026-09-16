# 主图叠加正交辅助线

默认在本次主参考图上制作辅助线版，随后把干净原图组与辅助线版一起交给候选生成器。它是投影方向的软约束，不是3D相机、深度控制或可证明的几何锁定。一次试验不能证明相对无线方案有提升。

## 准备和复用

1. 先读 [orthographic-geometry.md](orthographic-geometry.md) 并确定本轮相机：默认方位45°、俯角45°，对应地面轴屏幕斜率±0.707107，竖直方向向上；这是设计目标，不是参考实测。用户明确镜头覆盖优先。只匹配统一相机，不逐栋描线；不要将屏幕斜线也画成45°。
2. 按当前 imagegen 技能及工具协议，对主图做一次编辑：保持画幅、内容、构图和画风，叠加稀疏细线。地面X/Y轴各3–4条平行线，分别青色/品红；高度方向用约3条短黄色竖线。线跨越不同区域，不汇聚到消失点，不加文字、立方体或密集网格。只同方向的世界边应平行；不追踪坡屋顶斜边。
3. 实际查看输出，检查每组线近似平行、两组方向符合共同镜头且不遮挡大量细节。记录编辑是否改变原图，不能声称像素保持。明显方向错误或严重重绘最多额外修正一次；仍不可用则报告辅助线准备失败，不默默降级或宣称启用成功。
4. 保存 `references/camera-guides.png` 与 `references/camera-guides.prompt.txt`（实际英文 prompt）。不同参考组分目录保存；修正加版本号保留历史。仅当主图、方位、俯角与本轮camera规格均未改变时，不为每候选重复生成辅助线。
5. 候选输入顺序为原始1–3张干净图，随后附加辅助线图，再附当前候选布局草图，共3–5张；原图不删减。若用户已经提供明确配对且可用的辅助线版，查看并复用，不重复派生。完整输入无法通过当前工具传入时说明缺失项并请求补齐，不拼图、不漏图。若用户明确禁用辅助线，记录 disabled 并沿用原有流程。

## 英文辅助线编辑模板

```text
Edit the supplied primary reference to create an orthographic camera-guide overlay.
Preserve the original framing, scene content, object arrangement, colors and drawing style as closely as possible. Add only sparse thin construction lines.
Target shared projection: [actual shared camera specification; default azimuth 45 degrees, elevation 45 degrees, projected ground-axis slopes +0.707107 and -0.707107, upright verticals; these are design parameters, not measured reference angles].
Add 3–4 cyan parallel lines for one ground-plane axis, 3–4 magenta parallel lines for the other, and about 3 short yellow vertical segments distributed across the scene for upright height. Keep each line family straight and parallel, without convergence or vanishing points. Use one coherent basis across the entire image, not separate guides tracing each existing building. Lines must remain visible without obscuring the underlying art. No labels, cubes, borders, or additional objects. Return one image in the original aspect ratio.
```

填写目标方向后才调用；候选生成使用 prompt-template.md 中的参考分工段，明确相机规格与已校验草图控制几何，辅助线必须与它们一致、干净图负责画风，且最终画面完全移除标记。辅助线不要求复制原图地形或限制三候选的布局变化。

## 结果检查与报告

逐张查看上中下区域中同朝向建筑的墙基、水平檐口和桥面；检查竖向线与同尺寸重复物体的尺度。不要把屋顶坡度、物体真实尺寸差异或地面旋转误判为镜头漂移。记录具体可见偏差及辅助线残留；遵从主流程的每槽位最多一次修正上限。只有目视判断时明确写“目视”，不报告未测量角度或透视合格率，也不自动宣称比旧流程更好。
