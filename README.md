# Subconverter Config

自用的 [subconverter](https://github.com/tindy2013/subconverter) 代理规则配置管理，基于 [ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) 规则集定制。

通过模块化的 Snippet 片段系统，组合生成面向不同场景的 Clash 配置文件（`[custom]` 模式）。

## 配置概览

| 配置文件 | 场景 | 说明 |
|---------|------|------|
| `General.ini` | 通用 | 包含基础规则 + 回家策略组 |
| `General-share.ini` | 通用（可分享） | 仅基础规则，不含回家等私有策略 |
| `Work.ini` | 公司网络 | 基础规则 + 回家 + 公司屏蔽（知乎、B站、抖音等） |
| `Work-share.ini` | 公司网络（可分享） | 基础规则 + 公司屏蔽，不含回家 |
| `Router.ini` | 路由器 | 基础规则 + PT 下载 + 影音刮削（TMDB） |

`-share` 后缀的配置不包含私有策略（如回家），适合分享给他人使用。

## 目录结构

```
.
├── Config/                  # 生成的最终配置文件（CI 自动同步）
│   ├── General.ini
│   ├── General-share.ini
│   ├── Work.ini
│   ├── Work-share.ini
│   └── Router.ini
├── Ruleset/                 # 自维护的规则集文件
│   ├── AIGC.list            # AI 服务（OpenAI、Gemini、Claude 等）
│   ├── Direct.list          # 直连规则（自有域名、设备 IP 等）
│   ├── GoHome.list          # 回家规则（10.0.0.1/24）
│   ├── MediaScraper.list    # 影音刮削（TMDB）
│   ├── PrivateTracker.list  # PT 站点
│   ├── Proxy.list           # 需代理的站点
│   └── WorkProxy.list       # 公司网络需代理的站点
└── Snippets/                # 配置片段（编辑这里）
    ├── base.ini             # 基础配置标志
    ├── profiles.yaml        # 配置组合定义
    ├── build_configs.py     # 构建脚本
    ├── ruleset/             # 规则集片段
    ├── custom_proxy_group/  # 策略组片段
    └── emoji/               # 节点 emoji 映射片段
```

## 工作原理

配置生成采用 **片段拼装** 的方式，将规则集、策略组、emoji 映射分别维护为独立片段，通过 `profiles.yaml` 定义组合方式：

```
Snippets/
  ruleset/
    基础.txt          ← 公共规则集（直连、拦截、媒体、电报等）
    俺要回家.txt       ← 回家规则集
    公司屏蔽.txt       ← 公司网络屏蔽规则
    PT下载.txt         ← PT 站点规则
    影音刮削.txt       ← TMDB 刮削规则
  custom_proxy_group/
    基础.txt          ← 公共策略组（节点选择、自动选择等）
    超低倍率.txt       ← 低倍率节点策略组
    俺要回家.txt       ← 回家策略组
    公司屏蔽.txt       ← 公司屏蔽策略组
    PT下载.txt         ← PT 策略组
    影音刮削.txt       ← 影音刮削策略组
  emoji/
    基础.txt          ← 国家/地区 emoji 映射
    回家.txt           ← 回家节点 emoji
```

`profiles.yaml` 中每个 profile 通过 `from`（本地片段）或 `url`（远程片段）拼装。没有 `before` 时按声明顺序追加；需要插入已有内容中间时使用 `before`，策略组按组名定位，规则集按规则地址定位。

### profiles.yaml 示例

```yaml
profiles:
  general:
    output: Config/General.ini
    ruleset:
      - from: 基础
      - before: https://raw.githubusercontent.com/Sowevo/subconverter/main/Ruleset/AIGC.list
        from: 俺要回家
    custom_proxy_group:
      - from: 基础
      - before: 🌍 国外媒体
        from: 地区自动选择
      - before: 🎯 全球直连
        from: 智能助手地区
      - before: 🎯 全球直连
        from: 俺要回家
    emoji:
      - from: 回家
      - from: 基础
```

## 本地构建

需要 Python 3.11+。

```bash
# 预览生成结果（输出到 Snippets/generated-preview/）
python3 Snippets/build_configs.py

# 写入正式配置（输出到 Config/）
python3 Snippets/build_configs.py --write-config
```

## 自动同步

推送 `Snippets/` 目录的变更后，GitHub Actions 会自动运行 `build_configs.py --write-config` 并将生成的 `Config/*.ini` 提交回仓库。

参见 [`.github/workflows/sync-config.yml`](.github/workflows/sync-config.yml)。

## 如何新增一个配置

1. 在 `Snippets/ruleset/` 下新建规则集片段（如 `MyFeature.txt`）
2. 在 `Snippets/custom_proxy_group/` 下新建对应策略组片段
3. 在 `Snippets/profiles.yaml` 中添加新 profile，引用上述片段
4. 推送后 CI 自动生成对应的 `Config/*.ini`

## 策略组说明

| 策略组 | 类型 | 说明 |
|-------|------|------|
| 🚀 节点选择 | select | 手动选择节点 |
| ♻️ 自动选择 | url-test | 自动测速选优，排除低质量节点 |
| 📉️ 超低倍率 | fallback | 优先使用 0.5 倍率/测试节点 |
| 🤖 智能助手 | url-test | AIGC 专用，限定日韩中新加坡美英德印 |
| 🏠 俺要回家 | select | 回家节点（🏠 标记） |
| 🎬 影音刮削 | load-balance | TMDB 刮削负载均衡 |
| 🕹 PT下载 | select | PT 站点专用 |
| 💼 公司屏蔽 | select | 公司网络被屏蔽站点的代理 |
| 🎯 全球直连 | select | 直连流量 |
| 🛑 全球拦截 | select | 广告拦截 |
| 🍃 应用净化 | select | 应用内广告净化 |
| 🐟 漏网之鱼 | select | 兜底规则 |

## 致谢

- [subconverter](https://github.com/tindy2013/subconverter) - 订阅转换后端
- [ACL4SSR](https://github.com/ACL4SSR/ACL4SSR) - 规则集参考
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script) - 部分规则来源
- [SukkaW/Surge](https://github.com/SukkaW/Surge) - AIGC 规则参考
