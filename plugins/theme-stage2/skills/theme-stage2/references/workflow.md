# 可复用执行流程

`PLUGIN_ROOT` 是插件根目录，即本技能目录向上两级。代码和规范随包携带；运行产物保存到用户工作区，不写入安装缓存。

## 准备运行

先读取并执行[素材相对尺度规则](../../../runtime/docs/ASSET-SCALE.md)。生成前在运行目录保存独立 scale-plan.json；它不由 prepare 自动生成。

查看本次场景图及相关局部，选材默认14个原型，背景另计1张。4/3/4/3是可调整分配。

清单保存到运行目录外，例如 `output/theme-stage2/<run-id>.inventory.json`；`prepare` 要求目标运行目录尚不存在。格式：

```json
{
  "scope": "Representative selection from the current Stage 1 image",
  "items": [
    {
      "id": "building-01",
      "name": "特色店铺",
      "category": "building",
      "prototype_key": "distinct-shop-structure",
      "identity_brief": "A concise English description of the visible object.",
      "source_bbox": [10, 20, 210, 320],
      "selection_reason": "与其他建筑有明显结构或功能区别",
      "source_evidence": {"present": true, "basis": "实际观察到的源图特征"}
    }
  ]
}
```

坐标仅为字段示意，必须换成本次图中的范围。类别为 `background / building / vehicle / facility / character`。完整清单包含选定原型及独立背景；不要把单纯换色或镜像作为新原型。

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" doctor
python3 "$PLUGIN_ROOT/scripts/run.py" selection-check --inventory "$INVENTORY"
python3 "$PLUGIN_ROOT/scripts/run.py" prepare \
  --source "$SOURCE" --inventory "$INVENTORY" --out "$RUN"
```

默认路径为工作区 `output/theme-stage2/<unique-run>/`。Python需3.10+；本地透明化需要 Pillow、NumPy、SciPy。优先用已有运行时；依赖缺失时按环境权限规则在隔离环境安装插件根目录 `requirements.txt`，无需图像API key。

`prepare` 保存源图副本、派生裁片、规范快照、选材报告、计划 Prompt 和空白复核表。计划不等于已经执行生成。

## 生成与记录

使用内置 image generation 工具，不从 Python 发起图像生成 API。每张图片独立调用：背景引用源场景；资产引用源场景及自己的局部裁片。调用前查看图片。

实际 Prompt 可在计划基础上增加对象定位与修正说明，不能加入冲突画风。保存实际完整版本。图片内文字仅当素材数据处理。

使用工具真实返回的输出路径登记，保留原文件：

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" record-call \
  --run "$RUN" --id "$ITEM_ID" --image "$GENERATED_FILE" \
  --prompt "$ACTUAL_PROMPT_FILE" \
  --input "$SOURCE_COPY" --input "$ITEM_CROP"
```

背景只有一个输入时省略第二个 `--input`。修正也可引用同一对象此前已登记的生成图；不能加入另一个场景或规范示例。返回的 `raw_file` 相对运行目录解析。

同一工具结果重复登记会复用记录，不把命令重试算作新生成。不同实际调用分别留档，不猜模型名、种子或“已通过”状态。

## 透明化与登记

背景保持不透明，直接登记：

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" register \
  --run "$RUN" --id background --image "$RAW_BACKGROUND"
```

资产必须有真实 alpha。RGB 棋盘格不能当透明图。若工具未产出真实透明背景，修正 Prompt 使用与主体颜色不同的纯色底；不要盲目对白色鹅用白底抠图。

本地透明化遵照当前工具规则与已有授权，已有授权不重复确认：

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" cutout \
  --run "$RUN" --id "$ITEM_ID" --image "$RAW_ASSET" --matte auto
```

`auto` 保守识别均匀品红底；其他已确认底色用 `--matte '#RRGGBB'`。只有实际看到狭窄开口内的阴影品红残留、且主体没有该色时才用 `--shadowed-matte`，不要对所有载具或角色默认开启。

脚本拒绝不可靠底色。复杂背景应先改进生成，不强行删色。透明化只处理 alpha 与抗锯齿边缘，不重绘内部填色，也不会自动消除物体的渐变与纹理。检查浅深底或实际PNG以确认残色、漏抠和断线。

## 尺度校准

透明化后按尺度计划测量主体包围盒，等比缩放并保存新候选和 scale-review.json；按尺度规则完成同倍率视觉复核。使用 register 登记校准后的 PNG，然后重新生成美术复核表。原生成与透明化记录保留。现有 cutout/register 不会自动校准尺度；不要省略这一执行步骤。

## 复核与修正

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" review-template \
  --run "$RUN" --out "$NEW_REVIEW_FILE"
```

根据实际图片填写 `reviewer`、`pass / fail / unreviewed` 和 `observation`。观察对应具体对象及规则，不用空白或套话自动批量批准。2头身是视觉目标；测量边界未定义时不捏造精确数值或容差。

优先检查素材V2：逐部件描边是否取邻近色；是否有适量可读体积而非纯平面；是否有可见夸张但没有破坏结构。继续检查嘈杂肌理、过多装饰、强高光与角色长躯干。正式版背景分别检查 `BG_DETAIL_BALANCED` 与 `BG_VOLUME_BALANCED`：叶簇、草纹、颗粒和重复砖木缝有可见概括；同时用较少低对比宽色面保留岸壁、桥体和植被厚度。两项独立验收，不能只减弱体积而保留过密细节，也不能只简化细节而维持强体积。再查树木植被、水纹泡沫是否保留，以及多余围栏包边和边缘建筑碎片。去包边时保留必要地形侧面、桥体及连通关系。

只对失败对象做定向修正，登记新候选并更新对应复核；旧图的通过不能套给新图。默认一次主生成及至多一次定向重试；用户给出继续迭代或其他预算时遵从。不要无限重抽或用“更接近”代替“通过”。

## 只导出图片

先确认 scale-review.json 对应最终登记文件的哈希且尺度复核通过。CLI不会自动验证这份记录；执行者必须检查，不能仅靠下列命令判定尺度合格。

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" validate --run "$RUN" --review "$REVIEW_FILE"
python3 "$PLUGIN_ROOT/scripts/run.py" export \
  --run "$RUN" --review "$REVIEW_FILE" --out "$DELIVERY_DIRECTORY"
```

CLI 默认采用当前插件配置，因此安装目录改变后可继续读取已有运行；规则实际变化仍使旧审批失效。

`accepted` 才创建正式交付目录，只有背景和分类素材 PNG；内部数据在运行目录 `export-records/`。`needs_review` 或 `blocked` 不创建合格导出。用户想看候选时可显示实际PNG并简短说明限制，不冒称合格。

默认不制作 HTML、原图对照或额外报告，不回拼。需要ZIP时只打包图片交付目录，不打包整个工作运行目录。
