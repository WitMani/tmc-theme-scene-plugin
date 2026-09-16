# 脚本叠加正交辅助线

默认使用本地 `scripts/camera_guides.py` 在主参考图副本上添加稀疏辅助线，不调用 imagegen。这是用户授权的确定性标注操作，不重绘参考图。辅助线是生成时的软提示，不保证成品严格遵循投影。

## 生成与复用

1. 读取 orthographic-geometry.md，确定与 A/B/C 草图相同的相机。脚本直接复用 `orthographic_layout.Camera` 的投影矩阵；默认方位45°、俯角45°，屏幕地面轴斜率为±0.707107，Z轴竖直。非默认镜头从布局JSON传入，并保留用户覆盖依据。
2. 执行：

```bash
python3 "$SKILL_DIR/scripts/camera_guides.py" \
  --source "$PRIMARY_REFERENCE" \
  --scene "$LAYOUT_SCENE_JSON" \
  --out "$RUN/references/camera-guides.png"
```

`--scene`可传scene.json或已校验布局JSON；省略时用默认相机。脚本依赖Pillow，输出PNG及同名JSON，不覆盖源图或已有结果，修订使用新文件名。保持原图像素尺寸，不拉伸参考图；非正方形参考的线方向仍由像素空间投影决定。
3. 自动检查每条线与投影轴同向、源文件未改动、线条以外像素不变。JSON记录源图/输出哈希、相机矩阵和端点。实际查看PNG，确认线条稀疏、可见且没有大量遮挡。自动通过只代表叠加几何正确，不能代替目视审核或成品检查。
4. A/B/C共用同一参考组、同一镜头的一张辅助图。参考或相机改变后重新生成。输入顺序仍为完整干净参考组 → 辅助线图 → 当前已审核草图。

## 失败处理与记录

脚本错误先修正输入、依赖或参数，不转回AI绘线，不消耗成品生图重试预算。若仍不可用，记录 `camera_guides.status=disabled_due_to_error` 及错误，使用完整干净参考组＋已审核草图＋文字相机约束继续；调整prompt编号并删除辅助图专属描述。用户明确要求辅助线必须成功时才暂停。

manifest记录 `method=deterministic_script`、源图、输出PNG/JSON路径、实际命令、相机参数、自动检查与目视结论；不再虚构辅助线生图调用或英文编辑prompt。旧AI辅助线失败记录保留，新脚本结果另存。

成品检查建筑墙基、水平檐口和桥面是否共享投影；坡屋顶斜边与旋转物体不要求沿辅助轴。成品不得残留线条、网格或标记。成品明显镜头漂移仍按原有单槽位修正预算处理。
