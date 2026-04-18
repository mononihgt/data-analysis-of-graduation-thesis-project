## 接下来要进行数据分析和绘图工作：

1. 绘图规范：按照CNS配图风格，包括palette, width of axis/bar edges, etc.. . Keep each chart looking nice and readable
2. use subthread to carry each task, and your job is unify palette and style of each subworker
3. 对于要绘制散点的地方，可以考虑使用透明度增加可阅读性。
4. 不管是散点还是bar，有关所有被试的图里面都要在需要的地方增加标准误的绘制
5. 一些文件结构和数据要求见 docs/ 文件夹
6. 统计检验要根据数据分布选择合理的检验方法，并且要输出txt文档，报告检验方法和检验结果
7. 对于所有被试数据的柱状图，需要绘制每个被试的散点
8. 所有图片都要绘制中文版和英文版，区别仅为label title等采用中文/英文，其他保持不变
9. 所有检验和绘图，都需要考虑如何统一奇数和偶数的情况，使奇数和偶数能够使用同样的figure进行呈现，参考 scripts/pdtask_d_error_analysis.py
10. 如果有不清楚的地方，可以参考实验代码，在 code_mpx/ 文件夹

> common knowledge
> • 真实值
>   - 六张脸的“真实二维值”定义在 src/params/load_MRpara.m:64；EP 任务里同一组值也出现在 src/params/load_EPpara.m:67。
>   - 这 6 组数是：
>       - F1 = [2.416, 4.788]
>       - F2 = [2.789, 7.765]
>       - F3 = [6.426, 8.527]
>       - F4 = [8.817, 6.716]
>       - F5 = [4.894, 2.020]
>       - F6 = [7.659, 3.185]
>   - 这组值常被映射到 400×400 的方框里，即约：
>       - F1 = [97, 192]
>       - F2 = [112, 311]
>       - F3 = [257, 341]
>       - F4 = [353, 269]
>       - F5 = [196, 81]
>       - F6 = [306, 127]
### EP task

- 数据文件说明：
  - 对于每一名被试，同一天learning/test可能有多份数据，比如`EPtask_learning-43-2026-03-26.mat`/`EPtask_learning-43-2026-03-26-1.mat`以及`EPtask-2-2026-03-27.csv`/`EPtask-2-2026-03-27-1.csv`。这是由于规则是可以随意在测试和学习阶段进行切换，而实验完成的标准是在一次测试阶段连续正确完成6个试次。而每次进入学习或测试阶段都会生成一个新的文件。因此，XX-1，XX-2不是对之前文件的覆盖，而是需要一天内需要整合的多个文件

1. 对于每一名被试，对每一天的数据，根据explore/learning阶段的坐标点记录，在实验框定的矩形区域内绘制explore的移动轨迹（类似于眼动轨迹图），图中需要标注出六张面孔对应的能力值和温暖值的标定点
2. 对于每一名被试，对每一天的数据，根据explore/learning阶段的坐标点记录，在实验框定的矩形区域内绘制explore的移动轨迹的热力图（参考眼动的热力图），图中需要标注出六张面孔对应的能力值和温暖值的标定点
3. 对于每一名被试，绘制一个柱状图，横轴为天数，纵轴为学习时间（在explore阶段停留的时间），图中一共有三个bar
4. 对于每一名被试，绘制一个柱状图，横轴为天数，纵轴为测试阶段进行的试次数，图中一共有3个bar
5. 对于所有被试的数据，绘制2,3,4要求的图，并且在3和4的图中标注显著性
6. 对于所有被试的数据，可以考虑绘制explore的移动轨迹（类似于眼动轨迹图）是否合理，如果困难，可以不画

### SP task
1. 对于每一名被试，绘制折线图，横轴是试次编号，纵轴是每个试次的`rt`列的数据
2. 对于所有被试，绘制折线图，每条折线是一个被试的数据，横轴和纵轴和 1 相同。

### DJ task

- 实验说明
  - **已知，村庄A距离B比村庄A距离C更近（SubNo为偶数时，AC比AB更近）。同村庄的居民住的更近。** 该任务中，会依次呈现两对人物，你需要推断哪两个人物住得更近，若【第一对更近】按【左键】，【第二对更近】按【右键】。在第四个人物呈现时，尽快按键反应。每个【试次开始】时，屏幕会呈现【绿色】十字；【两对人物的间隔】，屏幕会呈现【紫色】十字。你可以依此判断现在屏幕上呈现的是第一对/第二对。
  实验分为练习和正式实验阶段。
  
1. 对于每个被试，绘制一个柱状图，根据横轴为两种`type`，分别为`type=1`和`type=3`，`type=3`涉及的是AB和AC距离的判别，xlabel记为`异村庄距离判别`，`type=1`涉及的是同村庄居民住的更近的判别，xlabel记为`同村庄距离判别`。纵轴是正确率，即该type的正确率。

### PD task

- 实验说明
  - 每个试次会呈现一对人物，你需要依次调整柱形复原他们能力和温暖值的差值和中点。试次之间，可能需要复原【当前人物对中点】和【上一对中点】的中点。
  
- 分析目标
  - 以奇数被试(`AB < AC`)为例。此处需要用到Varignon's Theorem。对AB村，共有A1,A2,B1,B2四张面孔
  > The midpoints of the sides of an arbitrary quadrilateral form a parallelogram. If the quadrilateral is convex or concave (not complex), then the area of the parallelogram is half the area of the quadrilateral.If one introduces the concept of oriented areas for n-gons, then this area equality also holds for complex quadrilaterals.The Varignon parallelogram exists even for a skew quadrilateral, and is planar whether the quadrilateral is planar or not. The theorem can be generalized to the midpoint polygon of an arbitrary polygon. 

1. 对于每个被试，需要绘制3张图
   - 在方框内绘制六张面孔的实际点。对于AB村，以AB村的四个点为顶点，绘制一个透明的凸四边形，并绘制实际的对边中点的中点。接着分别绘制实验中测量到的 median(median(a1,b1),median(a2,b2)), 也可能是median(median(a1,a2),median(b1,b2)),etc.. 根据实验而定，即需要绘制2次对边中点的中点
   - AC村和BC村同理，各画一张图
  > 实际绘制过程中，要考虑如何把奇数和偶数给统一起来，在图中能够统一的表现
2. 对于所有被试，需要绘制三张图
   - 在方框内绘制六张面孔的实际点，对于AB村，以AB村的四个点为顶点，绘制一个透明的凸四边形，并绘制实际的对边中点的中点。接着分别绘制所有被试实验中测量到的2次对边中点的中点
   - AC和BC村同理
3. 根据统一的模板重新调整 d_error_analysis 的 script, 并进行对应的统计检验
4. 检验D-near情况下2次对边的中点是否有显著差异；还是符合Varignon's theorem, 中点的中点重合


### CT task

> 能力值为left bar，温暖值为right bar

1. 对于每个被试，绘制一张图，图中绘制六张面孔的true position，然后绘制被试复原的24个点，面孔之间的scatter需要有区分，可以通过颜色
2. 对于所有被试，首先计算每个被试在对于每张面孔4次复原的平均值，然后和1相同，绘制true position，并绘制各个被试的复原position均值
3. 对每张面孔，检验所有被试复原的(能力值,温暖值)和(true 能力值, true 温暖值)是否有显著差异

> | 检验问题 | 参数方法（正态假设） | 非参数方法（稳健） |
> | :--- | :--- | :--- |
> | 两种条件差异 | 配对 Hotelling’s \(T^2\) | 多元符号/符号秩检验（`MNM`包） |
> | 样本 vs 固定点 | 单样本 Hotelling’s \(T^2\) | 同上 |

### MR task


> common knowledge
> • 真实值
>   - 六张脸的“真实二维值”定义在 src/params/load_MRpara.m:64；EP 任务里同一组值也出现在 src/params/load_EPpara.m:67。
>   - 这 6 组数是：
>       - F1 = [2.416, 4.788]
>       - F2 = [2.789, 7.765]
>       - F3 = [6.426, 8.527]
>       - F4 = [8.817, 6.716]
>       - F5 = [4.894, 2.020]
>       - F6 = [7.659, 3.185]
>   - 这组值常被映射到 400×400 的方框里，即约：
>       - F1 = [97, 192]
>       - F2 = [112, 311]
>       - F3 = [257, 341]
>       - F4 = [353, 269]
>       - F5 = [196, 81]
>       - F6 = [306, 127]

1. 对于每个被试，绘制两张图。
   - 根据被试实际调整的边框长度（`WarmthRange`,`AbilityRange`）绘制矩形，并绘制被试实际标记的六个坐标点。
   - 将被试在自己绘制的矩形里面标记的六个点，按照比例投射到正方形里面绘制，并在图中也绘制实际的六张面孔的点
2. 对于所有被试，绘制两张图
   - 绘制所有被试实际调节的边框（透明度调低），并绘制所有被试调节的边框的平均边框（不设置透明度）（mean warmthrange, meanabilityrange）
   - 在一个正方形里面，绘制真实的六张面孔的值，并绘制所有被试复原的投影过来的值
3. 检验所有被试绘制的矩形，长和宽是否有显著差异（即是否显著偏离方框）
4. 对于每张面孔，检验所有被试投影到方框之后，和真实值是否有显著差异