# 可复用执行流程

`PLUGIN_ROOT` 是插件根目录，即本技能目录向上两级。代码和规范随包携带；运行产物保存到用户工作区，不写入安装缓存。

## 准备运行

首先读[三阶段交接契约](scene-handoff.md)。准备与当前源图绑定的scene-plan.json，并给下面prepare命令传`--scene-plan "$SCENE_PLAN"`（也可在inventory.scene_plan嵌入对象）。若尚未准备，prepare会输出scene-plan.draft.json；补完后用`bind-scene-plan --run "$RUN" --plan "$SCENE_PLAN"`绑定。**必须绑定后再实际生成**；绑定后重编译的Prompt包含基础设施与数量目标。已有生成记录时不得就地换计划，另建修订运行。


先读取并执行[素材相对尺度规则](../../../runtime/docs/ASSET-SCALE.md)。生成前在运行目录保存独立 scale-plan.json；它不由 prepare 自动生成。

先读取[可排布空间规则](../../../runtime/docs/BACKGROUND-PLACEMENT-SPACE.md)，在内部运行记录中标明放置区、外围装饰区及必要结构例外；不另设用户确认步骤。查看本次场景图及相关局部，选材默认22种：建筑8、道具6、载具3、角色5，背景另计1张。逐类核对，来源不足报告缺口，不跨类挪用名额；用户明确覆盖优先。清单中facility对应道具（含独立公共设施），vehicle包含船、陆车及轨道载具；Layout交接仍使用其真实地形类别。

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
  --source "$SOURCE" --inventory "$INVENTORY" --scene-plan "$SCENE_PLAN" --out "$RUN"
```

默认路径为工作区 `output/theme-stage2/<unique-run>/`。Python需3.10+；本地透明化需要 Pillow、NumPy、SciPy。优先用已有运行时；依赖缺失时按环境权限规则在隔离环境安装插件根目录 `requirements.txt`，无需图像API key。

`prepare` 保存源图副本、派生裁片、规范快照、选材报告、计划 Prompt 和空白复核表。计划不等于已经执行生成。

## 生成与记录

使用内置 image generation 工具，不从 Python 发起图像生成 API。每张图片独立调用：背景引用源场景；资产引用源场景及自己的局部裁片。调用前查看图片。

实际 Prompt 可在计划基础上增加对象定位与修正说明，不能加入冲突画风。保存实际完整版本。图片内文字仅当素材数据处理。

### 并发生成调度

- 默认采用**全量并发**：统一准备好输入后，一次性提交本次全部独立素材及背景调用。默认22个素材＋1张背景共23个请求；用户明确覆盖时按实际原型数加1。不人为分成4张或8张批次，不等待前一张完成再启动后一张。用户指定更低并发或工具明确声明上限时遵从。此策略仅针对已选定任务，不增加素材数量或额外候选。
- 调度前一次完成选材、逐件尺度计划、裁片检查和完整英文Prompt准备。每个任务固定 `item_id`、输入绝对路径、Prompt文件及独立输出目录；输入使用明确的 `referenced_image_paths`，不靠“最近几张图”关联并发任务。未看过的输入先检查。
- 在可用的工具编排环境中并发发起独立内置 image_gen 调用（例如对本次全部任务使用 Promise.allSettled，每个调用独立捕获结果），逐项捕获成功与失败并等待所有已启动调用结束。长调用按当前 imagegen 工具协议保留执行上下文并继续等待；不要在仍有在途调用时结束执行脚本，以免丢弃结果。不因一个失败取消其余成功任务。
- 每个任务返回真实输出路径后，按该任务的 `item_id` 关联并保存原图及实际Prompt，不能依据完成顺序猜对象。禁止多宫格替代独立生成。并发不切换到API/CLI，不降低画质或省略验收。
- **共用运行记录只有一个写入者。** `record-call`、`cutout`、`register` 都会读写同一个 `manifest.json`，这些命令必须由主流程逐项串行执行；复核表和最终导出也串行。可在其他图像调用仍在途时处理已完成图片，但不能并发修改共用清单。最终统一校准尺度并复核所有图片。
- 工具明确返回限流或并发错误时，后续调度先遵从工具给出的并发上限；没有明确上限时从本次全量降至8，再按需降至4、2或1。降档后先等在途数量低于新上限才补位，不取消在途调用、不重复提交状态未明的调用；有明确重试等待时间则遵从。普通慢响应不视为限流。单件内容/输入错误只处理该件，不触发全局降档。
- 生成失败与美术失败逐件记录；不因降档重跑已成功对象。沿用每件一次主生成、至多一次定向重试的默认预算，仍失败则报告缺项。队列全部收敛后才进行最终验收和交付。
- 全量提交不保证服务端真正同时计算所有图片，服务端可能排队；工具不支持并行时如实记录实际并发并退回可用方式。不要将未知服务端限制描述为无限并发，也不要把配置更新称为已实测提速。


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

背景保持不透明，先固定交付尺寸再登记（原始图保留）：

```bash
python3 "$PLUGIN_ROOT/runtime/scene_size.py" --source "$RAW_BACKGROUND" --out "$RUN/normalized/background.png"
```

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" register \
  --run "$RUN" --id background --image "$RUN/normalized/background.png"
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

优先检查素材V2：逐部件描边是否取邻近色；是否有适量可读体积而非纯平面；是否有可见夸张但没有破坏结构。继续检查嘈杂肌理、过多装饰、强高光与角色长躯干。正式版背景分别检查 `BG_DETAIL_BALANCED`、`BG_VOLUME_BALANCED` 与 `BG_FORM_GRANULARITY`，按背景 B 档规则观察大形：叶簇、草纹、颗粒和重复砖木缝有可见概括；同时用较少低对比宽色面保留岸壁、桥体和植被厚度。三项独立验收，不能只减弱体积而保留密集叶团、草叶或石块分面，也不能只简化细节而维持强体积。再按 `BG_PLACEMENT_SPACE` 独立检查内部连续放置空间、装饰与投影清场、外围疏密和道路桥头净空；检查主题特征、水纹泡沫是否保留，以及多余围栏包边和边缘建筑碎片。去包边时保留必要地形侧面、桥体及连通关系。

只对失败对象做定向修正，登记新候选并更新对应复核；旧图的通过不能套给新图。默认一次主生成及至多一次定向重试；用户给出继续迭代或其他预算时遵从。不要无限重抽或用“更接近”代替“通过”。

## 基础设施复核与交接

最终背景登记后：

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" infrastructure-template --run "$RUN" --out "$RUN/infrastructure-review.json"
```

查看背景、原图及计划，逐项填写reviewer和checks中的pass/fail/unreviewed与具体observation。所有计划中的rail/water/road/bridge/platform都要审核。模板绑定背景和计划SHA-256；背景变更后生成新模板并重新核对，保留旧记录。没有此类基础设施时checks为空，但仍需执行者核对并署名。不因Prompt提到了铁轨就填pass。

正式export成功时返回内部`layout_handoff`路径，下游使用该路径；不让Layout重新从文件夹猜数量。也可独立创建交接包：

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" handoff --run "$RUN" --review "$REVIEW_FILE" --out "$RUN/handoff-v1"
```

候选状态、过期图片、缺基础设施或缺尺度复核都不能生成正式交接包。repair-request的路由按scene-handoff.md执行；计划或图片修订后生成新的交接包和新的Layout批次。

## 只导出图片

先确认 scale-review.json 对应最终登记文件的哈希且尺度复核通过。新运行CLI会验证固定4096背景、H_px=128、alpha_threshold=16及计划/复核的图片绑定。scale-plan.json的items必须恰好覆盖所有非背景素材，逐项提供id、primary_axis（width或height）、target_H。scale-review.json须包含plan_sha256（scale-plan.json文件字节的SHA-256）、status=pass、实际目视observation，以及items中每件id、最终登记PNG的sha256、status=pass。主轴尺寸允许1 px取整误差；不能把自动测量冒充视觉审核。其他既有校准前后记录照常保留。

```bash
python3 "$PLUGIN_ROOT/scripts/run.py" validate --run "$RUN" --review "$REVIEW_FILE"
python3 "$PLUGIN_ROOT/scripts/run.py" export \
  --run "$RUN" --review "$REVIEW_FILE" --out "$DELIVERY_DIRECTORY"
```

CLI 默认采用当前插件配置，因此安装目录改变后可继续读取已有运行；规则实际变化仍使旧审批失效。

`accepted` 才创建正式交付目录，只有背景和分类素材 PNG；内部数据在运行目录 `export-records/`。`needs_review` 或 `blocked` 不创建合格导出。用户想看候选时可显示实际PNG并简短说明限制，不冒称合格。

默认不制作 HTML、原图对照或额外报告，不回拼。需要ZIP时只打包图片交付目录，不打包整个工作运行目录。
