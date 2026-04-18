# Analysis Roadmap

## Purpose
本文件记录后续各任务的数据分析、统计检验与绘图需求。它是“待实现清单”，不是当前代码状态说明。

## Global Standards

### Figure Style
- 统一图形风格，保持同一套 palette、坐标轴线宽、bar edge width、字体层级与留白。
- 散点密集时优先通过透明度提升可读性。
- 所有涉及全部被试的 bar 图，需叠加每个被试的散点，并在合适位置绘制标准误。
- 所有图均输出中文版和英文版，两者仅文字标签不同，图形结构与配色保持一致。

### Statistics And Outputs
- 统计检验应根据数据分布选择合适方法，不强行使用参数检验。
- 每项统计分析应输出对应的文本结果摘要，报告检验方法、样本量、统计量与 `p` 值。
- 若存在奇偶被试条件翻转，图示与统计都应先统一重编码，再进入汇总与比较。

### Shared References
- 六张面孔的 canonical ground truth 见 `docs/face-ground-truth.md`。
- 所有涉及坐标点的绘图、汇总与检验，都应先按被试/日期对应的 `squareSidePx` 放缩，再统一回到共享的 0–10 空间。
- 不同被试、不同日期的屏幕分辨率可能不同；同一被试的 EP task day 3 与其后立即完成的任务共享同一个屏幕配置块。
- 仓库层面的文件结构、验证流程与硬约束见 `docs/architecture.md`、`docs/development.md` 与根目录 `AGENTS.md`。
- 若需要核对实验实现细节，可参考实验代码目录 `code_mpx/`。

## Task Requirements

### EP Task

#### Data Handling
- 同一被试同一天可能存在多份 `learning` 或 `test` 文件，例如 `XX.mat` 与 `XX-1.mat`。
- 这些文件是同一天内多个阶段的追加记录，不是覆盖关系；分析时需要按“被试 × 日期”整合。
- 不同被试、不同日期的 `squareSidePx` 可能不同；学习与测试分析应先恢复该 `被试 × 日期` 的缩放，再统一输出到 0–10 空间。
- day 3 推断出的 `squareSidePx` 还是同一被试后续任务的共同缩放基准。

#### Per-Subject Outputs
- 对每个被试、每一天绘制 `explore/learning` 阶段移动轨迹图，并在 0–10 空间标注六张面孔的真实能力值与温暖值位置。
- 对每个被试、每一天绘制 `explore/learning` 阶段热力图，并在 0–10 空间标注六张面孔真实位置。
- 对每个被试绘制按天汇总的学习时间柱状图，纵轴为 explore 停留时间。
- 对每个被试绘制按天汇总的测试试次数柱状图。

#### Group-Level Outputs
- 汇总全部被试，绘制热力图、学习时间图与测试试次数图。
- 对学习时间图和测试试次数图标注显著性。
- 如可行，再评估是否绘制全体被试的综合移动轨迹图；若信息过载，可不做。

### SP Task
- 对每个被试绘制折线图：横轴为试次编号，纵轴为 `rt`。
- 对所有被试绘制总览折线图：每条折线代表一名被试。

### DJ Task

#### Design Note
- 村庄距离规则受被试奇偶影响：奇数被试 `AB < AC`，偶数被试 `AC < AB`。
- 同村庄居民距离更近。

#### Per-Subject Outputs
- 对每个被试绘制正确率柱状图，按 `type` 分两类：
  - `type = 1`：同村庄距离判别
  - `type = 3`：异村庄距离判别
- 纵轴为该 `type` 下的正确率。

#### Group-level Outputs
- 对所有被试绘制正确率柱状图，绘图结构和subject-level相同
  - 要求在柱状图的基础上添加每名被试的散点以及最低正确率(horizontal line)

### PD Task

#### Design Focus
- 任务要求被试复原人物对的差值与中点，部分试次需要进一步复原“当前中点”和“上一对中点”的中点。
- 该分析需要统一奇偶被试的条件翻转，并参考 Varignon's theorem 组织图示与比较。
- 统计解释限制见 `docs/pdtask-main-effect.md`。

#### Per-Subject Outputs
- 每个被试另绘 1 张 `d_error` 条件图：横轴为重编码后的 `same` / `near` / `far` / `unknown`，纵轴为统一到 0–10 空间后的 `d_error`；图中应同时保留该被试的 trial-level 散点和条件均值。
- 每个被试绘制 3 张图，对应 `AB`、`AC`、`BC` 三组村庄关系。
- 每张图需要：
  - 在 0–10 空间画出六张面孔的真实点位；
  - 对对应四张脸画透明凸四边形；
  - 画真实对边中点的中点；
  - 叠加实验中测得的两次“对边中点的中点”估计。

#### Group-Level Outputs
- 对全部被试分别绘制 `AB`、`AC`、`BC` 三张汇总图。
- 汇总图中保留 0–10 空间里的真实点位、真实中点中点，以及所有被试测得的两次估计。

#### Analysis Work
- 在统一模板下维护 `scripts/proc4_pdtask_analysis.py`。
- 检验 `D-near` 情况下两次对边中点的中点是否存在显著差异，即是否符合 Varignon 预期的重合关系。

### CT Task

#### Display Convention
- `left bar` 表示能力值，`right bar` 表示温暖值。

#### Per-Subject Outputs
- 对每个被试绘制一张图：0–10 空间中的真实六张面孔位置 + 被试复原的 24 个点。
- 不同面孔的散点需要可区分，优先通过颜色区分。

#### Group-Level Outputs
- 先计算每个被试对每张面孔 4 次复原的均值，再在 0–10 空间绘制真实点位与各被试均值点。

#### Statistics
- 对每张面孔检验所有被试复原坐标与真实坐标是否显著不同。
- 建议的二维检验框架：

| 检验问题 | 参数方法（正态假设） | 非参数方法（稳健） |
| :--- | :--- | :--- |
| 两种条件差异 | 配对 Hotelling’s \(T^2\) | 多元符号 / 符号秩检验（`MNM`） |
| 样本 vs 固定点 | 单样本 Hotelling’s \(T^2\) | 同上 |

### MR Task

#### Shared Reference
- 真实点位使用 `docs/face-ground-truth.md` 中的 canonical coordinates。
- 所有复原点在绘图与统计前统一放缩到 0–10 空间。

#### Per-Subject Outputs
- 对每个被试绘制两张图：
  - 按其实际调节的 `WarmthRange` 与 `AbilityRange` 画矩形，并绘制被试标记的六个点；
  - 将该矩形内的六个点按比例投射回 0–10 空间，再与真实六张面孔点位共同绘制。

#### Group-Level Outputs
- 绘制所有被试实际调节的矩形叠加图，并单独标出平均矩形。
- 在统一的 0–10 空间中绘制真实六张面孔与所有被试投影后的点。

#### Statistics
- 检验所有被试绘制矩形的长宽是否存在显著差异。
- 对每张面孔检验投影后的群体复原点与真实点是否显著不同。
