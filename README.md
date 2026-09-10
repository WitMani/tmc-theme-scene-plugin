# 主题场景工坊 · Theme Scene Studio

基于最终 C 方案的 Codex 主题迁移插件。用户提供 **1–3 张参考图**（默认 1 张）和主题清单，每个主题生成 **3 张不同布局的候选图**。

## 生成规则

- 原图提供美术风格、镜头、比例与细节参考，目标主题决定背景、地形和建筑布局。
- 多张参考图组成同一参考组，默认第一张主导画风，其余补充细节。参考图数量不乘入输出数量。
- 采用同色系描边、轻量配色与低反光材质，保留建筑辨识度和柔和体积。
- 每个候选独立引用同一参考组，使用英文 prompt；主要通过地块、建筑群和通路组织形成差异。
- 内置 20 个主题，也支持自定义建筑、角色、载具和道具清单。
- 大画幅颜色斑驳作为后续处理项记录；不导出碰撞、导航或可玩关卡数据。

## 调用示例

安装插件后，在任务中附上参考图并输入：

```text
使用 $theme-scene-studio，参考这张图，生成威尼斯主题的三张候选。
```

```text
使用 $theme-scene-studio，参考这三张图，以第一张为主风格，
生成预设 2 和 5，每个主题各三张候选。
```

第二个示例输出 6 张候选图。每张都会保存实际英文 prompt 和检查记录。

## 仓库结构

```text
.codex-plugin/plugin.json
skills/theme-scene-studio/
  SKILL.md
  agents/openai.yaml
  references/
    prompt-template.md
    candidates.md
    themes.md
```

- [技能入口](skills/theme-scene-studio/SKILL.md)：输入契约、生成流程、验收与交付。
- [最终 C 英文模板](skills/theme-scene-studio/references/prompt-template.md)：美术风格继承与三项视觉优化。
- [候选设计规则](skills/theme-scene-studio/references/candidates.md)：三张候选的差异与完成定义。
- [20 个主题预设](skills/theme-scene-studio/references/themes.md)：主题名称与元素清单。

本插件使用 Codex 环境中可用的内置图像生成工具，不包含独立的模型 API 客户端。输出默认保存到当前工作区的 `output/theme-scene-studio/<唯一运行目录>/`。
