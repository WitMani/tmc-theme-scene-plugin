# 最终 C：英文基础模板

先选择用户提供的1–3张参考图；用户未提供图片时使用随技能打包的 assets/default-reference.png 一张。查看实际参考图后，填入编号与角色，再填写主题。所有候选共享这个基础段，最后按 candidates.md 添加各自差异段。本文模板完整包含最终C方案，不依赖旧技能目录或实验图片。

```text
Create one complete casual-game scene in the requested theme.

REFERENCE AND PRIORITIES
The supplied reference group contains [N: 1, 2 or 3] images. Reference 1 is the primary source for the art style, camera and proportions; additional references supplement compatible shape and structural details. Follow any explicit roles below. The reference group is the reference for the drawing language, camera, shape proportions, character-to-building scale, structural detail density, and stylized surface treatment. Preserve its coherent game-asset appearance. Apply the outline, palette, and material refinements below even where the references use black contours, heavy dark colors, or strong highlights.
Reference roles and observed characteristics: [identify each input image in order, its role, common traits, and primary-image traits].

THEME
Theme: [name and subtitle].
Buildings: [elements].
Characters: [elements].
Vehicles: [elements].
Props and environment: [elements].
World organization: [only the necessary theme-appropriate land, water, circulation and elevation design].

The theme may reshape the background, terrain, roads, waterways, parcels and building arrangement. Preserve the reference camera type and requested framing, not its exact terrain topology. Keep a consistent family of recognizable assets, readable gaps, appropriate repetition, and small character proportions. Retain meaningful architectural features and moderate rounded volume while controlling incidental decoration.

COLOR-AWARE OUTLINES
Use clean, consistent outlines whose hues are derived from the neighboring fill colors. Prefer a moderately darker, chromatic shade of the local color family over uniform black contours. Choose a boundary color with enough contrast to separate adjacent objects. Keep outer contours readable and interior structural lines restrained. Do not remove outlines.

LIGHT, CHROMATIC PALETTE
Create a relaxed, light casual-game palette. Reduce the area occupied by heavy dark colors and achromatic extremes. Prefer softly tinted off-whites, colored light tones, and chromatic dark accents over large regions of pure white or pure black. Keep theme identity and clear hue/value separation. Preserve necessary small dark details such as eyes; do not wash out all contrast or desaturate the whole scene.

RESTRAINED MATERIAL RESPONSE
Reduce the strength and area of specular highlights and reflections. Favor softly matte or gently satin surfaces. Avoid white streaks, brushed-looking white marks, shiny rims, bright reflective edge trim, and aged ornamental material effects. Convey materials with color, a few structural marks, broad shading and gentle localized gradients. Preserve volume and identifying building details without adding realistic microtexture or flattening assets into bare geometric icons.

SCENE COHERENCE
Use theme-appropriate infrastructure. Boats belong in navigable water; land vehicles belong on ground routes; bridges connect reachable surfaces. Avoid arbitrary rivers in themes that do not support them. Keep the background calm and prevent foliage, debris and small decorations from overwhelming the asset silhouettes.

Maintain coherent large color fields and consistent lighting across the canvas. Follow the requested output framing and UI treatment; for scene-only output, include no UI, text, timers, buttons, borders or watermarks.
```

保持相同参考组；默认第一张主导，共性优先，不平均混合不兼容画风。输入只有一张时删除additional references等不适用句子。不要把占位符直接发给生成器。斑驳是后续事项，不视为已解决。

默认图是实际图片输入，不是纯文本模式。使用默认图时 N=1，并在参考角色中说明它是内置河畔村落画风参考；不要继承其中人类角色，目标角色依主题定义。文件路径按 SKILL.md 所在目录解析，并通过图像工具的图片引用参数传入。
