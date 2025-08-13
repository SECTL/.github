#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SECTL 贡献值计算系统
计算公式：贡献值 = （合并PR×5分） + （Commits×3分） + （文档×4分） + （有效Issues×2分） + （Code Review×2分）
时间范围：2025.8.1到2026.1.31
计算仓库：SecRandom, SecRandom-docs
"""

import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Any
import os
import sys
import urllib3
from dateutil import parser, relativedelta
from tabulate import tabulate
from tqdm import tqdm

# 禁用SSL证书验证警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class ContributionCalculator:
    def __init__(self):
        self.github_token = os.getenv('GITHUB_TOKEN', '')
        # 如果没有token，使用无认证请求（有速率限制）
        if self.github_token:
            self.headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        else:
            self.headers = {
                'Accept': 'application/vnd.github.v3+json'
            }
            print("警告：未设置GITHUB_TOKEN环境变量，将使用无认证请求（有速率限制）")
        self.start_date = datetime(2025, 8, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2026, 1, 31, 23, 59, 59, tzinfo=timezone.utc)
        self.repos = ['SECTL/SecRandom', 'SECTL/SecRandom-docs']
        self.contributors_data = {}
        
    def make_request(self, url: str) -> Dict[str, Any]:
        """发送GitHub API请求"""
        try:
            # 禁用SSL证书验证以解决证书验证失败问题
            response = requests.get(url, headers=self.headers, verify=False)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return {}
    
    def get_repo_contributors(self, repo: str) -> List[Dict[str, Any]]:
        """获取仓库的贡献者列表"""
        url = f"https://api.github.com/repos/{repo}/contributors"
        return self.make_request(url)
    
    def get_user_commits(self, repo: str, username: str) -> List[Dict[str, Any]]:
        """获取用户在指定仓库的提交记录（排除README.md相关提交）"""
        url = f"https://api.github.com/repos/{repo}/commits"
        params = {
            'author': username,
            'since': self.start_date.isoformat(),
            'until': self.end_date.isoformat()
        }
        # 禁用SSL证书验证以解决证书验证失败问题
        response = requests.get(url, headers=self.headers, params=params, verify=False)
        if response.status_code == 200:
            commits = response.json()
            # 过滤掉README.md相关的提交
            filtered_commits = []
            readme_keywords = ['readme', 'README.md', 'README', 'readme.md']
            
            for commit in commits:
                commit_message = commit.get('commit', {}).get('message', '').lower()
                # 检查是否包含README相关关键词
                if not any(readme_keyword in commit_message for readme_keyword in readme_keywords):
                    filtered_commits.append(commit)
            
            return filtered_commits
        return []
    
    def get_user_prs(self, repo: str, username: str) -> List[Dict[str, Any]]:
        """获取用户在指定仓库的PR记录"""
        url = f"https://api.github.com/repos/{repo}/pulls"
        params = {
            'state': 'closed',
            'author': username,
            'since': self.start_date.isoformat(),
            'until': self.end_date.isoformat()
        }
        # 禁用SSL证书验证以解决证书验证失败问题
        response = requests.get(url, headers=self.headers, params=params, verify=False)
        if response.status_code == 200:
            prs = response.json()
            # 只计算已合并的PR
            merged_prs = [pr for pr in prs if pr.get('merged_at') and 
                        self.start_date <= datetime.fromisoformat(pr['merged_at'].replace('Z', '+00:00')) <= self.end_date]
            return merged_prs
        return []
    
    def get_user_issues(self, repo: str, username: str) -> List[Dict[str, Any]]:
        """获取用户在指定仓库的Issues记录"""
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {
            'state': 'closed',
            'creator': username,
            'since': self.start_date.isoformat(),
            'until': self.end_date.isoformat()
        }
        # 禁用SSL证书验证以解决证书验证失败问题
        response = requests.get(url, headers=self.headers, params=params, verify=False)
        if response.status_code == 200:
            return response.json()
        return []
    
    def get_user_reviews(self, repo: str, username: str) -> List[Dict[str, Any]]:
        """获取用户在指定仓库的Code Review记录"""
        url = f"https://api.github.com/repos/{repo}/pulls"
        params = {
            'state': 'all',
            'since': self.start_date.isoformat(),
            'until': self.end_date.isoformat()
        }
        # 禁用SSL证书验证以解决证书验证失败问题
        response = requests.get(url, headers=self.headers, params=params, verify=False)
        if response.status_code == 200:
            prs = response.json()
            reviews = []
            for pr in prs:
                reviews_url = f"https://api.github.com/repos/{repo}/pulls/{pr['number']}/reviews"
                # 禁用SSL证书验证以解决证书验证失败问题
                reviews_response = requests.get(reviews_url, headers=self.headers, verify=False)
                if reviews_response.status_code == 200:
                    pr_reviews = reviews_response.json()
                    user_reviews = [review for review in pr_reviews if review['user']['login'] == username]
                    reviews.extend(user_reviews)
            return reviews
        return []
    
    def count_documentation_contributions(self, repo: str, username: str) -> int:
        """计算文档贡献数量（仅SECTL/SecRandom-docs仓库的所有提交都算文档贡献）"""
        # 只有SecRandom-docs仓库的提交才算文档贡献
        if repo != 'SECTL/SecRandom-docs':
            return 0
        
        commits = self.get_user_commits(repo, username)
        return len(commits)
    
    def calculate_user_contribution(self, username: str) -> Dict[str, Any]:
        """计算单个用户的贡献值，分别计算两个仓库后合并"""
        repo_data = {}
        total_prs = 0
        total_commits = 0
        total_docs = 0
        total_issues = 0
        total_reviews = 0
        
        for repo in self.repos:
            # 获取PR数量
            prs = self.get_user_prs(repo, username)
            repo_prs = len(prs)
            total_prs += repo_prs
            
            # 获取Commit数量（已自动排除README.md）
            commits = self.get_user_commits(repo, username)
            repo_commits = len(commits)
            total_commits += repo_commits
            
            # 获取文档贡献数量（仅SecRandom-docs仓库）
            docs = self.count_documentation_contributions(repo, username)
            total_docs += docs
            
            # 获取Issues数量
            issues = self.get_user_issues(repo, username)
            repo_issues = len(issues)
            total_issues += repo_issues
            
            # 获取Code Review数量
            reviews = self.get_user_reviews(repo, username)
            repo_reviews = len(reviews)
            total_reviews += repo_reviews
            
            # 计算单个仓库的贡献值
            repo_score = (
                repo_prs * 5 +      # 合并PR×5分
                repo_commits * 3 +  # Commits×3分
                docs * 4 +         # 文档×4分
                repo_issues * 2 +   # 有效Issues×2分
                repo_reviews * 2    # Code Review×2分
            )
            
            # 保存仓库数据
            repo_name = repo.split('/')[-1]
            repo_data[repo_name] = {
                'prs': repo_prs,
                'commits': repo_commits,
                'docs': docs,
                'issues': repo_issues,
                'reviews': repo_reviews,
                'score': repo_score
            }
        
        # 计算总贡献值
        contribution_score = (
            total_prs * 5 +      # 合并PR×5分
            total_commits * 3 +  # Commits×3分
            total_docs * 4 +     # 文档×4分
            total_issues * 2 +   # 有效Issues×2分
            total_reviews * 2    # Code Review×2分
        )
        
        return {
            'username': username,
            'prs': total_prs,
            'commits': total_commits,
            'docs': total_docs,
            'issues': total_issues,
            'reviews': total_reviews,
            'score': contribution_score,
            'repo_data': repo_data
        }
    
    def get_all_contributors(self) -> List[Dict[str, Any]]:
        """获取所有贡献者并计算贡献值（带进度条）"""
        all_users = set()
        
        # 收集所有用户
        for repo in self.repos:
            contributors = self.get_repo_contributors(repo)
            for contributor in contributors:
                all_users.add(contributor['login'])
        
        # 计算每个用户的贡献值（带进度条）
        results = []
        print("🔄 正在计算贡献者数据...")
        for username in tqdm(all_users, desc="处理用户", unit="用户"):
            user_data = self.calculate_user_contribution(username)
            if user_data['score'] > 0:  # 只包含有贡献的用户
                results.append(user_data)
        
        # 按贡献值排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results
    
    def generate_leaderboard_md(self) -> str:
        """生成贡献值排行榜的Markdown格式（使用tabulate优化版）"""
        contributors = self.get_all_contributors()
        
        # 使用tabulate生成总体排行榜
        headers = ["排名", "👤 用户名", "🔀 合并PR", "💻 Commits", "📚 文档贡献", "🐛 Issues", "👀 Code Review", "⭐ 贡献值"]
        table_data = []
        
        for i, contributor in enumerate(contributors, 1):
            table_data.append([
                f"**{i}**",
                f"**{contributor['username']}**",
                str(contributor['prs']),
                str(contributor['commits']),
                str(contributor['docs']),
                str(contributor['issues']),
                str(contributor['reviews']),
                f"**{contributor['score']}**"
            ])
        
        overall_table = tabulate(table_data, headers=headers, tablefmt="github")
        
        md_content = f"""### 🏆 贡献值排行榜

> 📊 **贡献值计算公式**：贡献值 = （合并PR×5分） + （Commits×3分） + （文档×4分） + （有效Issues×2分） + （Code Review×2分）
> 
> 📅 **统计时间范围**：{self.start_date.strftime('%Y.%m.%d')} - {self.end_date.strftime('%Y.%m.%d')}
> 
> 🏗️ **统计仓库**：{', '.join(self.repos)}
> 
> ⚠️ **注意**：已排除README文件相关贡献统计

#### 📋 总体排行榜

{overall_table}

---

#### 📊 各仓库详细统计

"""
        
        # 添加各仓库详细统计
        for contributor in contributors:
            repo_headers = ["仓库", "🔀 合并PR", "💻 Commits", "📚 文档贡献", "🐛 Issues", "👀 Code Review", "⭐ 分数"]
            repo_table_data = []
            
            for repo_name, repo_data in contributor['repo_data'].items():
                repo_table_data.append([
                    f"**{repo_name}**",
                    str(repo_data['prs']),
                    str(repo_data['commits']),
                    str(repo_data['docs']),
                    str(repo_data['issues']),
                    str(repo_data['reviews']),
                    f"**{repo_data['score']}**"
                ])
            
            repo_table = tabulate(repo_table_data, headers=repo_headers, tablefmt="github")
            md_content += f"##### 👤 {contributor['username']} (总分: {contributor['score']})\n\n{repo_table}\n\n"
        
        md_content += f"*📅 最后更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"
        
        return md_content
    
    def update_readme(self, readme_path: str):
        """更新README文件，插入贡献值排行榜"""
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 生成新的贡献值排行榜
            leaderboard_md = self.generate_leaderboard_md()
            
            # 查找插入位置（在星标历史之前）
            insert_marker = "### 星标历史 ✨"
            if insert_marker in content:
                # 替换旧的贡献值排行榜（如果存在）
                old_leaderboard_start = "### 🏆 贡献值排行榜"
                old_leaderboard_end = "### 星标历史 ✨"
                
                if old_leaderboard_start in content:
                    # 删除旧的贡献值排行榜
                    start_idx = content.find(old_leaderboard_start)
                    end_idx = content.find(old_leaderboard_end)
                    content = content[:start_idx] + content[end_idx:]
                
                # 插入新的贡献值排行榜
                content = content.replace(insert_marker, leaderboard_md + "\n\n" + insert_marker)
            
            # 写入文件
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("README.md 更新成功！")
            
        except Exception as e:
            print(f"更新README.md失败: {e}")

if __name__ == "__main__":
    calculator = ContributionCalculator()
    
    # 更新README.md
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    print(f"🔄 正在更新README.md文件: {readme_path}")
    calculator.update_readme(readme_path)
    print("✅ README.md更新完成！")
    
    # 输出贡献值数据
    contributors = calculator.get_all_contributors()
    
    # 使用tabulate生成控制台表格
    print("\n🏆 贡献值排行榜：")
    print("=" * 80)
    
    headers = ["排名", "用户名", "PR", "Commit", "文档", "Issue", "Review", "总分"]
    table_data = []
    
    for i, contributor in enumerate(contributors, 1):
        table_data.append([
            str(i),
            contributor['username'],
            str(contributor['prs']),
            str(contributor['commits']),
            str(contributor['docs']),
            str(contributor['issues']),
            str(contributor['reviews']),
            str(contributor['score'])
        ])
    
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    print("\n" + "=" * 80)
    print("📊 各仓库详细统计：")
    print("=" * 80)
    
    # 输出各仓库详细统计
    for contributor in contributors:
        print(f"\n👤 {contributor['username']} (总分: {contributor['score']})")
        
        repo_headers = ["仓库", "PR", "Commit", "文档", "Issue", "Review", "分数"]
        repo_table_data = []
        
        for repo_name, repo_data in contributor['repo_data'].items():
            repo_table_data.append([
                repo_name,
                str(repo_data['prs']),
                str(repo_data['commits']),
                str(repo_data['docs']),
                str(repo_data['issues']),
                str(repo_data['reviews']),
                str(repo_data['score'])
            ])
        
        print(tabulate(repo_table_data, headers=repo_headers, tablefmt="pretty"))
    
    print("=" * 60)
    print(f"统计时间：{calculator.start_date.strftime('%Y-%m-%d')} 至 {calculator.end_date.strftime('%Y-%m-%d')}")
    print(f"统计仓库：{', '.join(calculator.repos)}")