# SECTL 贡献值计算系统使用说明

## 系统概述

SECTL 贡献值计算系统是一个自动化的贡献者价值评估工具，用于统计和展示组织内成员在指定仓库中的贡献情况。

### 计算公式

```
贡献值 = （合并PR×5分） + （Commits×3分） + （文档×4分） + （有效Issues×2分） + （Code Review×2分）
```

### 统计范围

- **时间范围**：2025年8月1日 - 2026年1月31日
- **统计仓库**：
  - https://github.com/SECTL/SecRandom
  - https://github.com/SECTL/SecRandom-docs

## 系统组成

### 1. 贡献值计算脚本 (`contribution_calculator.py`)

这是核心计算脚本，负责：
- 通过GitHub API获取仓库数据
- 计算每个贡献者的各项指标
- 生成贡献值排行榜
- 自动更新README.md文件

### 2. GitHub Action工作流 (`.github/workflows/contribution.yml`)

自动化工作流，负责：
- 定期（每天）运行计算脚本
- 自动提交更新
- 处理可能的错误情况

### 3. README.md展示页面

在组织首页展示：
- 贡献值排行榜表格
- 计算公式说明
- 统计范围说明
- 最后更新时间

## 设置说明

### 1. GitHub Token设置

为了能够访问GitHub API，需要设置GitHub Token：

1. 在GitHub仓库中，进入 `Settings` > `Secrets and variables` > `Actions`
2. 点击 `New repository secret`
3. 创建名为 `GITHUB_TOKEN` 的secret
4. 值设置为具有适当权限的GitHub Personal Access Token

**Token所需权限**：
- `repo` - 完整仓库访问权限
- `read:user` - 读取用户信息

### 2. 手动运行脚本

如果需要手动运行贡献值计算：

```bash
# 安装依赖
pip install requests

# 设置环境变量
export GITHUB_TOKEN="your_github_token_here"

# 运行脚本
cd .github/profile
python contribution_calculator.py
```

### 3. 手动触发GitHub Action

1. 进入仓库的 `Actions` 页面
2. 选择 `更新贡献值排行榜` 工作流
3. 点击 `Run workflow` 按钮
4. 选择分支并点击 `Run workflow`

## 功能详解

### 1. 合并PR统计 (5分/个)

- 统计在指定时间范围内已合并的Pull Request
- 只计算状态为`closed`且`merged_at`不为空的PR
- 跨仓库累加计算

### 2. Commits统计 (3分/个)

- 统计用户在指定时间范围内的所有提交
- 通过GitHub API的commits端点获取
- 包含所有分支的提交

### 3. 文档贡献统计 (4分/个)

- 通过分析commit message识别文档相关贡献
- 关键词匹配：`doc`, `docs`, `documentation`, `readme`, `md`, `markdown`, `文档`, `说明`
- 自动识别文档更新提交

### 4. Issues统计 (2分/个)

- 统计用户创建且已关闭的Issues
- 只计算状态为`closed`的Issues
- 排除Pull Request（在GitHub中PR也被视为Issue类型）

### 5. Code Review统计 (2分/个)

- 统计用户对Pull Request的Review活动
- 包含所有类型的Review（评论、批准、请求更改等）
- 跨所有PR统计Review数量

## 数据更新机制

### 自动更新

- **触发频率**：每天UTC时间00:00（北京时间早上8:00）
- **更新内容**：重新计算所有贡献者的贡献值
- **提交方式**：自动提交到main/master分支

### 手动更新

- **触发方式**：手动触发GitHub Action
- **适用场景**：测试、紧急更新、调试

### 错误处理

- 如果自动更新失败，系统会创建Pull Request
- Pull Request包含详细的错误信息
- 维护者可以手动审查和合并

## 注意事项

### 1. API限制

- GitHub API有请求限制（未认证：60次/小时，认证：5000次/小时）
- 系统会自动处理API限制和错误
- 建议使用认证Token以避免限制

### 2. 时间范围

- 所有统计都基于UTC时间
- 时间范围硬编码为2025.8.1-2026.1.31
- 如需修改时间范围，需要更新脚本中的`start_date`和`end_date`变量

### 3. 仓库范围

- 当前只统计SecRandom和SecRandom-docs两个仓库
- 如需添加更多仓库，修改脚本中的`repos`列表

### 4. 数据准确性

- 系统依赖GitHub API的数据准确性
- 某些特殊情况（如删除的账户、合并的仓库）可能影响统计
- 建议定期检查数据准确性

## 故障排除

### 1. 脚本运行失败

**问题**：`requests.exceptions.RequestException`
**解决**：检查网络连接和GitHub Token有效性

**问题**：`403 Forbidden`
**解决**：更新GitHub Token或检查权限设置

### 2. GitHub Action失败

**问题**：权限错误
**解决**：检查仓库的Actions权限设置

**问题**：脚本执行超时
**解决**：检查API响应时间，考虑优化脚本

### 3. 数据不准确

**问题**：贡献值计算错误
**解决**：检查脚本中的计算逻辑和API响应

**问题**：时间范围不正确
**解决**：验证脚本中的时间设置

## 扩展功能

### 1. 添加新仓库

编辑`contribution_calculator.py`中的`repos`列表：

```python
self.repos = ['SECTL/SecRandom', 'SECTL/SecRandom-docs', 'SECTL/NewRepo']
```

### 2. 修改计算权重

编辑`calculate_user_contribution`方法中的权重设置：

```python
contribution_score = (
    total_prs * 5 +      # 修改PR权重
    total_commits * 3 +  # 修改Commit权重
    total_docs * 4 +     # 修改文档权重
    total_issues * 2 +   # 修改Issue权重
    total_reviews * 2    # 修改Review权重
)
```

### 3. 添加新的统计维度

可以在脚本中添加新的统计方法，并在计算公式中包含新维度。

## 联系支持

如果在使用过程中遇到问题，请通过以下方式联系：

- **GitHub Issues**：在仓库中创建Issue
- **QQ群**：833875216
- **Email**：lzy.12@foxmail.com

## 版本历史

- **v1.0.0** (2025-01-01)：初始版本，支持基本的贡献值计算和展示

---

*最后更新：2025-01-01*