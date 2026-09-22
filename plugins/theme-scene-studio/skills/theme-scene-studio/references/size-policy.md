# Stage 1 / Stage 2 统一尺寸规划

来源：2026-09-22用户尺寸修订及“对stage1也进行修改”。配置 `../scripts/size-v2.json` 与Stage 2的 `runtime/profiles/size-v2.json` 使用同一契约ID与完全一致内容，各插件携带副本以支持独立安装；交接时核对契约ID及配置，不依赖其他插件的绝对路径。

全图4096×4096。人物基体宽75、高130 px，发型服饰道具可超出。非人物小物件通常为非建筑，宽高各150–300 px；中物件宽高各301–500 px；大物件宽高各501–830 px，中大物件通常为建筑。尺寸是成品中的有效主体宽高，不是透明画布；保留比例，不拉伸成方形。细长或特殊对象记录例外依据。道路以所选车辆在同一地面投影中的横向宽度为1，道路净宽1–2.5；不能拿车辆长边代替车宽。

## 草图与构图

每个原型先记录 `size_class`、`target_wh_px`、`size_basis`，人物另记基体75×130和附件外扩；为物件及识别/操作间距预留地块。低分辨率草图按画布宽/4096统一换算，例如1024草图中人物基体约18.75×32.5，不能仍画75×130。宽高是屏幕投影尺寸，不直接当XYZ世界尺寸；通过共同相机投影检查占位是否符合目标，不为凑尺寸改相机。低矮中性占位仍需记录对应完整主体预计高度，不用细节化建筑替代占位。不得缩小物件或扩大道路来满足216实例目标；容量不足记录问题并调整地形及分组。

大型物件上限 `large_max_instances` 为用户的x，按地图摆放实例合计而非原型数。x尚未指定时为null，标记数量上限待配置；继续制作但不能声称上限检查通过。有明确x后，规划数量合计不得超限。不能把候选图中仅用于展示的原型数当成最终实例数。

## 交接与审核

新候选的scene-plan使用H_px=130，附 `size_policy_id: scene-4096-h130-v2`、`large_max_instances`、逐资产尺寸档及目标宽高；道路记录参考车辆ID、参考横向车宽与道路比例。配置文件随运行保存并记录其哈希。Stage 2继承对应候选的尺寸、数量及例外，不自行恢复旧H128。

成品统一到4096后，复核人物基体与附件、各档体量、道路横向净宽和地块容量是否协调，记录具体对象/位置及偏差。生图是比例指导，不承诺所有对象逐像素准确；规划数值、图像观察与精确测量分开记录。明显失比例按既有候选修正预算处理，不无限重抽。Stage 2进行独立素材测量和等比校准。历史产物不自动迁移。

## 2026-09-22 P1：可执行尺寸契约

H=130的新计划必须由`scripts/size_policy.py`（Stage 2为`runtime/size_policy.py`）校验，不能仅填H_px。`size_policy_id`固定为`scene-4096-h130-v2`，`size_policy_sha256`取当前随包size-v2.json的文件SHA-256；两阶段及Layout使用同一配置和校验模块副本。哈希不符或缺字段时，先修计划/创建复核修订，不静默沿用旧审批。H=128历史计划按原契约读取。旧H=130运行若没有新字段，需要显式补齐计划并重新复核，不能直接冒称新版验收通过。

scene-plan顶层必须含`large_max_instances`（未配置明确为null）和`road_sizes`（无道路为[]）。每个asset必须有`size_class`（character/small/medium/large）、`target_wh_px`、`size_basis`；人物另有`base_body_wh_px:[75,130]`。超出物件分档必须给出`size_exception:{reason,basis}`并目视复核；超大例外仍计入大型实例总数，不能靠改小档名逃过x上限。

每条road_sizes为`{id,vehicle_id,vehicle_width_px,clear_width_px,measurement_basis}`。vehicle_id指向class=vehicle的真实原型，宽度是在同一地面投影下的横向车宽/道路净宽。无车主题可用vehicle_id=null并填写reference_vehicle_basis。每段必须满足1≤clear_width_px/vehicle_width_px≤2.5，按不同宽度路段分别记录；配置校验不能替代实际背景检查。

Stage 1制作草图前按目标宽高规划，交接前运行scene_contract.py验证以上字段；保留当前配置副本与哈希。Stage 2在prepare保存policy/size-v2.json并绑定manifest指纹；bind-scene-plan自动从scene资产目标生成初始scale-plan.json，并把逐件目标编译到Prompt。已有scale-plan不会被覆盖，必须与scene中的尺寸字段保持一致。

scale-plan顶层包含同一策略ID/哈希、H_px=130、alpha_threshold=16；items继承上述尺寸字段，另写primary_axis和target_H（主轴目标像素/130）。校准保持等比，除主轴外还必须检查另一轴，1px仅用于栅格取整，不是美术比例容差。比例不符直接报告，不能拉伸。

人物无外扩时完整目标为75×130。发型/服饰/道具外扩时，target_wh_px记录完整主体目标；scale条目另需`source_body:{sha256,bbox:[left,top,right,bottom]}`，标注本次透明化输入中基体的边界（不包含外扩附件）。校准后记录变换后的base_body_bbox，检查基体75×130，完整附件保留。不能把带帽子全包围盒当成人体，也不能给其他图片套旧坐标。

最终图片登记并校准后运行`run.py size-review-template --run <RUN> --out <RUN>/size-review.json`，实际查看图片再填写reviewer、逐件status/observation及人物base_body_bbox。可参考calibration.json中的坐标，但必须核对基体语义。每条道路复核填写实际vehicle_width_px与clear_width_px、status/observation，绑定背景和参考车辆的当前哈希。大型上限null时large_limit_status必须为unconfigured；配置上限且计数合法才填pass。

正式validate/export同时检查规范快照、scene/scale一致性、两轴实测、人物基体标注、道路比值、上限及图像绑定复核。size-review还绑定scene-plan/scale-plan哈希，任一改变即失效。合格交接包携带尺寸配置、size-review、scale-plan和scale-review；Layout导入和项目固定副本保留并校验这些文件。默认PNG交付仍可交付已生成内容并披露缺项，不因正式门槛阻塞图片交付。
