# 45°正交草图：统一坐标与可执行校验

## 默认相机的准确含义

默认 `azimuth_deg=45`、`elevation_deg=45`，正交投影，无焦距、消失点或透视除法。方位角是绕世界竖轴的方向，俯角是相对水平面的向下观察角。它们不是画面斜线角度，也不是严格等轴测的约35.264°俯角。用户明确指定其他相机时才覆盖，并在 `override_reason` 记录原话或依据；参数是设计值，不冒充参考图测量结果。

令世界地面为 XY、向上为 Z，缩放 s，画布原点 (cx,cy)：

```text
screen_x = cx + s * (cos(a)*x - sin(a)*y)
screen_y = cy + s * (sin(e)*sin(a)*x + sin(e)*cos(a)*y - cos(e)*z)
```

默认45°/45°时地面轴的屏幕斜率为 ±0.707107，屏幕斜线角约±35.264°；地面圆投影为轴比约0.707107的椭圆。不要为了“45度”把所有地面边强画成屏幕±45°。竖直Z轴投影向上；等尺寸物体不随远近缩放。A/B/C复用同一角度、缩放、画布和原点。

## 生成接口

读取本文件后，布局设计者编写 `layout-A.scene.json`（B/C同理），调用打包脚本；不要重新手写一套不一致的投影。所有顶点、宽度、半径、高度都用世界单位。脚本输出中性低细节 SVG、PNG、含世界/画面顶点的 JSON 和 `.validation.json`。PNG需要本地 Pillow；缺失时使用已配置含Pillow的本地Python环境，不调用图像API制作草图。

```bash
python3 <skill>/scripts/orthographic_layout.py render <run>/layout-A.scene.json --output-prefix <run>/layout-A
python3 <skill>/scripts/orthographic_layout.py validate <run>/layout-A.json <run>/layout-B.json <run>/layout-C.json
```

输出已存在会拒绝覆盖，修改后使用 `layout-A-v2` 等前缀。设计数据另存原始scene.json。原始scene的说明字段（区域用途、物件群、连接、密度/环境规划）会保存在输出 `source_scene` 中。manifest引用实际采用版本。

最小接口示例（仅示范几何，不是通用关卡布局模板）：

```json
{
  "candidate_id": "A",
  "canvas": [1024, 1024],
  "camera": {"azimuth_deg": 45, "elevation_deg": 45, "scale": 20, "origin": [512, 512]},
  "regions": [{"id":"town","interaction":"clickable placements and local clearance"}],
  "object_groups": [{"id":"building-1","theme_role":"saloon"}],
  "connections": [{"from":"lane","to":"well","purpose":"clear approach"}],
  "design_notes": "Replace this example with the actual theme-specific layout.",
  "items": [
    {"id":"ground","kind":"polygon","role":"ground","points":[[-10,-10,0],[10,-10,0],[10,10,0],[-10,10,0]]},
    {"id":"lane","kind":"band","role":"route","points":[[-8,0,0],[8,0,0]],"width":1.2},
    {"id":"well","kind":"circle","role":"placement","center":[2,3,0],"radius":0.6},
    {"id":"building-1","kind":"box","role":"placement","center":[-3,3,0],"size":[2,2,0.6]},
    {"id":"edge-rock","kind":"polygon","role":"environment","points":[[-9,6,0],[-7,6,0],[-7,8,1],[-9,8,1]]}
  ]
}
```

支持 `polygon`、`polyline`、`band`（世界宽度的道路/桥面/铁路带）、`circle`（水平世界圆，支持不同Z高度）、`box`（低矮无屋顶占位，`rotation_deg` 为世界平面旋转）。`polyline`只表示轴线/轮廓，不能用屏幕笔画宽度充当道路宽度。`box`不规定最终建筑高度和外形；完整造型来自画风参考。内部不接受用户配色、材质、纹理或屋顶细节。地面先画，通路其次，体块按远近合理排序；描边宽度是注释笔画，不是物理宽度。

## 必须通过的检查

- 同一主题三个文件的camera字段完全一致；不得候选间改变缩放/原点来变相改镜头。
- 脚本重算角度对应的矩阵、每个世界顶点的投影，并从原始世界primitive重建几何；混入手画屏幕圆、修改屏幕点或不一致矩阵时验证失败。
- 校验平行相机行向量正交、等范数、地面圆椭圆关系和远近等长不变性；测试文件在 `tests/test_orthographic_layout.py`。
- 校验报告通过后仍须实际看PNG：地块/道路/桥/铁路符合主题，桥头无遮挡、路不穿屋、密度接近参考、环境边缘自然、A/B/C空间关系实质不同。脚本不验证碰撞、可玩性、审美或画风。
- 输出geometry已覆盖的形状之外，不得追加未经投影的屏幕形状。文字/图例放配套JSON或说明中，供图保持干净。

校验保证的是代码草图的投影一致性，不保证最终生成图精确45°。成品必须另行目视检查；发现画风漂移时先核对草图是否过度造型，而非继续加硬阴影、更多结构线或更大建筑。
