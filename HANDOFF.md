# Mechanics Agent Skills 任务交接与全景文档 (HANDOFF.md)

> **文档面向对象**：完全没有前期上下文的新会话 / 接手 Agent。  
> **最后更新时间**：2026-09-21  
> **当前代码库版本**：v3.1.0 (最新提交 commit `a733eb7`)  
> **代码仓库**：https://github.com/yq04/mechanics-agent-skills.git  
> **本地工作区**：`D:\1_Research\AI_Workspace\mechanics-agent-skills`  
> **全局技能目录**：`C:\Users\Administrator\.agents\skills\`

---

## 一、 我们在做什么任务 (Task & Project Scope)

### 1.1 项目核心定位与目标
本项目旨在为**固体力学（Solid Mechanics）、断裂力学（Fracture Mechanics）、弹性力学（Elasticity）与应用数学（Applied Mathematics）**领域打造一套生产级、证据驱动、零外部硬性运行依赖且严格遵循 **MIT 商业友好开源协议**的学术全生命周期 Agent 技能生态（**Mechanics Agent Skills Suite**）。

系统核心使命是解决通用 LLM 和通用学术检索工具在连续介质力学中的痛点：
- **符号与公式混淆**：通用模型极易自作聪明地“纠错”，篡改裂纹开度与单侧位移、混淆不同应力强度因子定义；
- **虚假引用与虚构页码**：文献工具常将无全文的摘要赋以“第 1 页”，形成伪证；
- **环境依赖脆弱**：依赖复杂的第三方 Python 包导致部署在多 Agent 运行时中极易因环境缺失而崩溃。

### 1.2 核心架构边界与协议红线
1. **纯正 MIT 许可证与 Clean-Room 实现**：
   - 调研了开源标杆 `academic-research-skills` (ARS v3.22.0)，但其采用 **CC BY-NC 4.0** 限制性协议。
   - **硬性红线**：严禁复制、vendor 其任何源码或提示词文本。本项目所有 7 大科学诚信门禁（G1~G7）和 5D 筛选器均采用完全独立的力学原生清洁室实现（Clean-room Implementation）。
2. **零外部硬性运行依赖的微内核设计**：
   - 核心库（`src/mechanics_skills/`）基础能力**仅依赖 Python 标准库**（`urllib`, `sqlite3`, `dataclasses`, `json`, `re`, `hashlib`, `math`, `pathlib`）。
   - 高级渲染与解析库（`matplotlib`, `numpy`, `pymupdf`, `httpx`）完全作为可选 extras（`[figure]`, `[pdf]`, `[http]`）通过惰性加载与安全降级保护，绝不在顶层强制导入，杜绝在纯净环境报 `ModuleNotFoundError`。
3. **学术严格性契约**：
   - 严格区分单侧位移 $w$ 与裂纹总开度 $\mathrm{COD} = 2w$；
   - 严格区分断裂力学中带 $\sqrt{\pi}$ 因子的大 $K_I = \sigma\sqrt{\pi a}$ 与小 $k_I = \sigma\sqrt{a}$；
   - 严格区分工程剪应变 $\gamma$ 与张量剪应变 $\varepsilon_{12}$；
   - 严格区分自洽数值计算与外部独立解析基准；
   - 严格区分真实 PDF 证据（`pdf_page: int`）与仅有摘要的文献（`source_type: "abstract"`, `pdf_page: null`）。

---

## 二、 已经完成了什么 (Completed Work)

经过两轮系统化建设与最新的架构排查收口，项目已具备全功能交付状态：

### 2.1 核心底层架构 (`src/mechanics_skills/`)
- **多源合规文献检索 (`providers/`)**：
  - `crossref.py`：严格遵守 `mailto` 礼貌池协议与指数退避，支持深层游标分页。
  - `openalex.py`：遵守 OpenAlex 官方最新规范（`per_page<=100`，突破 100 自动游标分页，10 req/s 速率控制）。
  - `arxiv.py`：强制 HTTPS 访问与 Atom XML 流式解析，单连接调度排队（最大 1 请求/3秒）。
  - `semantic_scholar.py` 与 `unpaywall.py`：实现合规的法律 OA 全文探测。
- **力学 5D 筛选引擎 (`screening.py`)**：
  - 覆盖本构(C)、几何(G)、势函数(P)、输出物理量(O)、方法论(M)五个正交维度的量规打分。
- **引文拓扑与主路径分析 (`citations.py`)**：
  - 构建正反向引文图，基于 Search Path Count (SPC) 拓扑权值算法提取理论演进主路径。
- **页码级证据抽取引擎 (`extraction.py`)**：
  - 精确抽取 $C_{ijkl}, S_{ijkl}$ 张量、断裂参量 $J, G, K$、复变势函数；严格锁定摘要无虚假页码。
- **出版级力学绘图引擎 (`figure.py`)**：
  - 内置 5 种经典力学模板：应力云图 (`stress_contour`)、SIF 响应曲线 (`sif_curve`)、相互作用热图 (`interaction_heatmap`)、渐近解与全场对比 (`asymptotic_comparison`)、裂纹几何拓扑图 (`crack_geometry`)。
  - 严格锁定单栏 85 mm、双栏 175 mm 出版物理尺寸，采用 Okabe-Ito 色弱友好色盘，输出 PDF/PNG/SVG 三格式与 `figure.manifest.json` 溯源清单。
- **公式保护学术润色 (`polishing.py`)**：
  - 建立不可动保护区，锁定行内/行间 LaTeX 公式、文献引用、物理单位与张量角标；剥离 AI 机械套话（`delve`, `pivotal`, `foster` 等）。
- **模拟同行评审与七大科学诚信门禁 (`reviewer.py` & `integrity.py`)**：
  - 针对 *JMPS*、*IJSS*、*EFM*、*Acta Mech Sinica* 期刊标准，实现五维健全度审计。
  - 部署贯穿全链路的 **7 大科学诚信门禁 (G1~G7)**：
    * **G1**：本构对称性与正定性验证、$\sigma \sim K r^{-1/2}$ 奇异性标度验证。
    * **G2**：引用与出处忠实度（杜绝虚假引用与摘要冒充全文）。
    * **G3**：数据出处可溯性（图表必须绑定原始数据哈希）。
    * **G4**：基准独立性（自洽测试与外部独立基准隔离）。
    * **G5**：伪物理现象防范（网格畸变/奇异截断误差防假冒新机理）。
    * **G6**：方法声明一致性（平面应变与平面应力核查）。
    * **G7**：理论假设范围锁定（小范围屈服与线弹性极值边界锁定）。
- **可恢复工作流编排 (`workflow.py`)**：
  - 贯通 `search -> screen -> citations -> oa -> extract -> figure -> polish -> peer-review -> integrity -> handoff` 全流程。
  - 采用输入 SHA-256 签名失效机制与真正跨平台的 `Path.replace()` 原子写入。

### 2.2 六大独立 Agent Skills（已规范构建并同步全局）
每个技能均包含标准 frontmatter 的 `SKILL.md`（<500 行）、`references/` 深度指南以及 `scripts/` 启动入口：
1. **`mechanics-scoping-review`**：系统性文献检索、5D 初筛、引文主路径与 PRISMA 综述生成。
2. **`openalex-database`**：全球 2.5 亿学术图谱实体查询、通用引用与学者统计助手。
3. **`mechanics-evidence-extraction`**：力学本构、断裂参数、势表述的真实页码级提取与证据矩阵构建。
4. **`mechanics-figure`**：固体力学出版级绘图引擎（85/175mm、Okabe-Ito 色盘、清单契约）。
5. **`mechanics-paper-polishing`**：力学论文语言润色、公式完整性锁定、术语护栏与 AI 套话清洗。
6. **`mechanics-paper-reviewer`**：模拟顶刊审稿人意见、五维科学健全性审核与有界反思修订。

### 2.3 分发构建与同步工具 (`tools/`)
- `tools/build_skill_bundles.py`：自动将核心库注入为自包含的 `scripts/_vendor/mechanics_skills/`，生成独立 zip 分发包。
- `tools/sync_skills.py`：支持 `--dry-run`，在更新时自动在目标目录的 `.backups/<timestamp>/` 创建安全备份，并严格限制六大技能白名单。
- **已全量同步到宿主全局技能库**：`C:\Users\Administrator\.agents\skills\`。

### 2.4 文档体系与工程规范 (`docs/`)
- [README.md](README.md)：完整的 6 技能矩阵、10 项统一 CLI 命令、Mermaid 流程图与 103/103 tests 徽章。
- [docs/architecture.md](docs/architecture.md)：微内核拓扑、模块职责、诚信门禁与 DAG 调度详解。
- [docs/provider-policy.md](docs/provider-policy.md)：Crossref, OpenAlex, arXiv, S2, Unpaywall 协议快照与配额。
- [docs/distribution.md](docs/distribution.md)：vendor 打包机制与同步备份策略。
- [docs/capability-status.md](docs/capability-status.md)：标准库微内核与可选 extras 对应表及当前已知限制。
- [plans/2026-09-21-mechanics-skills-roadmap.md](plans/2026-09-21-mechanics-skills-roadmap.md)：Astra 架构审查路线图（S0~S5 已全部完成）。

### 2.5 本轮会话收口的 P0 偏差修复
1. **微内核零依赖修复**：在 `figure.py` 和 `integrity.py` 中将 `matplotlib` 与 `numpy` 改造为惰性/受保护导入，消除纯标准库环境导入报错。
2. **消灭虚假页码**：`workflow._run_evidence_extraction` 从摘要抽取时强制设置 `source_type="abstract"` 且 `pdf_page=None`。
3. **清单名称对齐**：工作流引用的图件清单统一修正为 `figure.manifest.json`。
4. **同步工具安全备份**：`tools/sync_skills.py` 实现了覆盖前创建时间戳备份，且在 `--dry-run` 时不提前创建目标目录。
5. **工作流原子替换**：修复 `_save_manifest`，杜绝先 unlink 再 rename 导致的瞬态文件缺失。

### 2.6 测试套件与验证
- **测试覆盖**：18 个测试文件、103 个测试用例，覆盖全部检索、缓存、ID 解析、提取、绘图、润色、评审、门禁、打包与工作流。
- **测试结果**：`python -m pytest -q` **103 passed in 5.64s, 0 failed, 100% 绿色全通**。
### 2.7 仓库中英双语文档与 GitHub 远端同步 (Bilingual Landing & Remote Push)
- **Astra 方案制定**：依据用户指令调用 `gpt-6-astra`（`astra_architect`）产出 `plans/2026-09-21-bilingual-readme-plan.md`，确立默认简体中文、双语互链导航、契约边界及 103 项测试真实记录。
- **默认简体中文首页 (`README.md`)**：以顶级力学学术与开源工程标准全面重构，顶部嵌入 `[简体中文](README.md) | [English](README_en.md)` 导航栏，详述六大技能矩阵、10 项统一 CLI 命令、Mermaid DAG 编排流程、七大科学诚信门禁（G1~G7）与离线 103/103 绿色测试口径。
- **完整英文版文档 (`README_en.md`)**：提供等价完备的英文技术与学术文档，保证国际化科研人员与海外开源社区的无障碍接入。
- **远端同步**：本地代码、双语 README、执行计划与交接文档均已全量提交并推送到 GitHub 远端仓库（`origin/master`）。

---

## 三、 当前卡在哪 / 遗留事项 (Current Status & Leftovers)

当前**无任何阻塞性 Bug 或未提交代码**。系统底层与技能生态已完成闭环。

目前处于**真实课题案例试跑（Pilot Run）与发行候选（Release Candidate）准备阶段**：
1. **S6 阶段（小型真实案例试跑）留存**：
   - 目前所有 103 项测试均为离线 deterministic fixture/mock。
   - 遗留任务：可根据用户当前正在研究的具体力学课题（例如 Fabrikant TI 介质中的 Penny-shaped 裂纹、各向异性界面断裂），构造一组包含 1~3 篇真实文献 PDF、真实刚度张量与解析 SIF 曲线的小型示例，完整跑通端到端工作流并导出 `artifacts/pilot-run/`。
2. **发布候选版本号**：
   - 随 S6 案例完成后，可发布 v3.1.1 正式 Release Tag。

---

## 四、 下一步计划是什么 (Next Step Plan)

新会话接手后，建议按以下步骤继续推进：

### 阶段 1：用户课题定向案例接入（S6）
- [ ] 与用户确认当前的具体研究案例输入（例如：TI 介质共线裂纹相互作用、或单裂纹 SIF 渐近基准）。
- [ ] 将真实文献 PDF 或结构化文本放入案例目录，配置 `run.json`。
- [ ] 运行端到端工作流：`mechanics-workflow run <case-config> --output-dir artifacts/pilot-case`。
- [ ] 检查生成的 PRISMA 流程图、证据卡片、85mm 物理尺寸图件、公式保护润色对比及 JMPS 期刊审稿报告。

### 阶段 2：发布候选收口（Release Candidate）
- [ ] 打上 Git Release Tag（如 `v3.1.1`）。
- [ ] 如有需要，生成最终发行包 `dist/mechanics-agent-skills-v3.1.1.tar.gz`。

---

## 五、 有哪些踩过的坑绝对不要再踩 (Hard Pitfalls & Lessons Learned)

> **⚠️ 以下 8 条为血泪换来的硬性闸门与教训，新会话绝对不可违背！**

### 1. 致命号池限制：严禁在 `functions__exec` 脚本中调用 `notify()` 或 `yield_control()`
- **事故机理**：本开发环境通过 CLIProxyAPI (CPA) 代理池驱动 Gemini 模型。底层协议严格要求每一次 `functionCall` 只能配对一次同 ID 的 `functionResponse`。如果在 JS 脚本执行中途调用 `notify(...)`，会向响应队列额外塞入一个中间包，导致下一次工具调用的 ID 配对发生队列错位，直接抛出无法恢复的 HTTP 400：`antigravity executor: invalid Gemini function call history: functionResponse.id does not match functionCall.id`。
- **后果**：该错误会被立刻写入 SQLite 数据库与 session jsonl，**导致整个会话永久报废，再也无法发起任何工具调用**！
- **铁律**：所有工具执行结果必须在 JS 脚本结束时通过**唯一次 `text(...)`** 输出，绝对不要在脚本内调用 `notify()`，也不要调用 `yield_control()`！

### 2. 算力与额度纪律：绝对不要滥用 `gpt-6-astra`
- **背景**：本机同时接入了 ChatGPT Plus (Astra) 与 Gemini 号池。Astra 额度极其宝贵且有严格周期限额。
- **铁律**：日常代码修改、写测试、运行命令、读写文档、普通子代理隔离等操作，**必须严格默认使用父会话模型（Gemini）**！只有当用户显式输入 `/astra-plan` 或明确要求“请让 Astra 进行深度架构规划/重大理论推导”时，才允许单次派发 `gpt-6-astra`，并且必须设置 `fork_turns: "none"`（严禁 fork `all`，否则上下文直接爆炸）。规划一旦写入约定路径，Astra 必须立刻退出，后续实施全部交由 Gemini。

### 3. 多智能体协作纪律：长思考等待超时与 Turn 活跃维持
- **铁律**：调用 `wait_agent` 等待深度推理子代理时，超时时间 `timeout_ms` 推荐设置为 `180000` 到 `300000`（3~5 分钟），切忌使用 30s 等短超时进行轮询。
- **严禁无工具调用交还控制权**：当子代理还在后台运行且 `wait_agent` 发生超时唤醒时，如果主智能体仅回复纯文本而不发起下一次 `wait_agent` 调用，客户端会将当前 Turn 判定为结束（task_complete），导致前端过早把控制权扔给用户并频繁弹窗“› 继续！”。子代理未结束前，必须保持在循环中持续调用 `wait_agent`。

### 4. 微内核零依赖红线：严禁在顶层导入第三方包
- **踩坑**：此前在 `src/mechanics_skills/__init__.py` 导入 `integrity` 与 `figure`，而它们顶层又导入了 `matplotlib` 与 `numpy`。这导致在未安装 extras 的纯净环境中导入基础模块直接崩溃。
- **铁律**：`src/mechanics_skills/` 核心模块禁止顶层无保护导入 `matplotlib`, `numpy`, `pymupdf`, `httpx`。必须使用 `try...except ImportError` 保护并做优雅降级！

### 5. 严守开源协议纯洁性：严禁混入 ARS 代码
- **背景**：参考的 `academic-research-skills` 是 **CC BY-NC 4.0** 协议，不可用于纯商业或宽松开源。
- **铁律**：严禁直接复制代码或文本！所有门禁（G1~G7）、审稿标准必须立足固体力学实际，独立自主编写。确保本项目始终保持纯正清白的 **MIT** 许可证。

### 6. 力学领域的数学物理符号护栏（严防 AI 瞎改公式）
- **学术重坑**：一般学术润色工具往往认为力学公式有“笔误”而自作聪明地修改：
  * 把单侧位移 $w$ 强制改成开度 $\mathrm{COD}$，或者把 $\mathrm{COD}$ 误当成单侧位移导致开度翻倍；
  * 把断裂力学中的应力强度因子小 $k_I$ 与大 $K_I$ 搞混（两者的定义差了 $\sqrt{\pi}$ 因子）；
  * 把工程剪应变 $\gamma_{xy}$ 与张量剪应变 $\varepsilon_{xy}$ 搞混（差了 2 倍）。
- **铁律**：润色工具必须严格保护 LaTeX 区域与符号映射表，遇有歧义时标记为 `unknown` 或生成修改建议，绝对不可在未经人工确认下自动篡改公式。

### 7. 严谨的学术证据定位（拒绝虚假页码）
- **踩坑**：历史代码中，若文献只有摘要，提取时顺手给了 `page_number=1`，造成了事实上的“伪造证据页码”。
- **铁律**：在 `extraction.py` 与 `workflow.py` 中，必须严格区分 `abstract` 与 `pdf_page`。未读取真实 PDF 的证据，其页码必须忠实标记为 `null / unknown`，`source_type` 必须为 `abstract`。

### 8. 验证与审查节约准则 (Stop on Green)
- **踩坑**：模型容易陷入过度验证综合征——针对微小的局部改动，反复发散探索虚构的边缘场景，编写几十个无意义的测试用例，空耗数万 Token。
- **铁律**：遵循“按比例检验（Proportional Testing）”与“通过即止（Stop on Green）”。针对性测试 Exit 0 绿灯后立即收手，禁止无休止的自我重复验证。

---

## 六、 常用命令与快速验证速查

新会话接手后，若需快速核验当前项目健康度，可直接运行以下命令：

```powershell
# 1. 运行完整测试集 (103 项测试全部通过)
python -m pytest -q

# 2. 检查统一 CLI 帮助信息
python -m mechanics_skills.cli --help

# 3. 运行端到端离线工作流验证
python -m mechanics_skills.cli workflow run examples/workflow/run.json --offline --output-dir artifacts/workflow-test

# 4. 重新打包 6 大技能包
python tools/build_skill_bundles.py --out dist/skills

# 5. 安全同步至全局技能库 (自动创建时间戳备份)
python tools/sync_skills.py --source dist/skills --apply
```
