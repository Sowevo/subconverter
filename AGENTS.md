# AGENTS.md

本文件给在本仓库工作的自动化编码助手使用。请优先遵守本文件，再结合用户的当前指令行动。

## 项目概览

这是一个自用的 `subconverter` 配置管理仓库，用模块化片段生成 Clash/subconverter `[custom]` 配置。

核心关系：

- `Snippets/` 是主要编辑入口。
- `Config/*.ini` 是由 `Snippets/build_configs.py` 生成的最终配置文件，通常不要手工修改。
- `Ruleset/*.list` 是自维护规则集，会被 `Snippets/ruleset/*.txt` 通过 raw GitHub URL 引用。
- `.github/workflows/sync-config.yml` 会在 `Snippets/**` 变更后自动运行生成脚本，并提交更新后的 `Config/*.ini`。

## 目录职责

- `Snippets/base.ini`：生成配置的基础 `[custom]` 和全局开关。
- `Snippets/profiles.yaml`：定义各 profile 如何组合规则集、策略组和 emoji。
- `Snippets/build_configs.py`：配置生成脚本，Python 3.11+。
- `Snippets/ruleset/*.txt`：ruleset 片段；每行一般是不带 `ruleset=` 前缀的 `策略组,规则地址`。
- `Snippets/custom_proxy_group/*.txt`：策略组片段；每行一般是不带 `custom_proxy_group=` 前缀的策略组定义。
- `Snippets/emoji/*.txt`：emoji 映射片段；每行一般是不带 `emoji=` 前缀的映射定义。
- `Config/*.ini`：生成物。
- `Ruleset/*.list`：实际规则内容。

## 重要工作流

编辑配置逻辑时，优先改源文件：

1. 改规则命中内容：编辑 `Ruleset/*.list` 或 `Snippets/ruleset/*.txt`。
2. 改策略组行为：编辑 `Snippets/custom_proxy_group/*.txt`。
3. 改节点 emoji：编辑 `Snippets/emoji/*.txt`。
4. 改 profile 组合顺序或输出文件：编辑 `Snippets/profiles.yaml`。
5. 改生成逻辑：编辑 `Snippets/build_configs.py`。

不要直接修改 `Config/*.ini`，除非用户明确要求修改生成物本身。若误改了 `Config/*.ini`，应恢复该生成物，并把实际变更落到 `Snippets/` 或 `Ruleset/`。

## 生成与验证

预览生成，不写入正式配置：

```bash
python3 "Snippets/build_configs.py"
```

写入正式 `Config/*.ini`：

```bash
python3 "Snippets/build_configs.py" --write-config
```

常用验证：

```bash
git diff -- "Snippets" "Ruleset" "Config"
python3 "Snippets/build_configs.py"
```

如果修改了 `Snippets/` 且需要确认正式输出，运行：

```bash
python3 "Snippets/build_configs.py" --write-config
git diff -- "Config"
```

注意：`--write-config` 会更新生成物。执行前先确认用户是否希望本地同步 `Config/*.ini`。

## 生成脚本行为

`Snippets/build_configs.py` 的关键逻辑：

- 读取 `Snippets/profiles.yaml` 中的 profile。
- 从 `Snippets/ruleset/`、`Snippets/custom_proxy_group/`、`Snippets/emoji/` 按 `from` 引用片段。
- 也支持 `url` 远程片段；非 optional 远程片段拉取失败会报错。
- `at` 表示插入位置，超出范围会插入末尾，负数会视为 0。
- 片段行如果没有对应前缀，会自动补上 `ruleset=`、`custom_proxy_group=` 或 `emoji=`。
- `filter_group_options()` 会移除不存在的 `[]策略组` 引用，但保留 `DIRECT` 和 `REJECT`。
- 生成文件头部会包含 profile 名称、生成时间、规则集和策略组摘要。

## 当前 Profile

- `general-share` -> `Config/General-share.ini`：基础规则，可分享。
- `general` -> `Config/General.ini`：基础规则 + 回家 + 低倍率 + emoji。
- `work-share` -> `Config/Work-share.ini`：基础规则 + 公司屏蔽，可分享。
- `work` -> `Config/Work.ini`：基础规则 + 回家 + 公司屏蔽 + 低倍率 + emoji。
- `router` -> `Config/Router.ini`：基础规则 + 低倍率 + 影音刮削 + PT 下载。

`-share` 配置不应引入私有的回家策略或私有节点标记。

## 策略组注意事项

- `📉️ 超低倍率` 定义在 `Snippets/custom_proxy_group/超低倍率.txt`。
  - 当前匹配 `🧪` 或形如 `0.x` 的小于 1 倍率节点。
  - 不要只改 `Config/*.ini` 中生成出来的同名策略组。
- `🤖 智能助手` 定义在 `Snippets/custom_proxy_group/基础.txt`。
  - 当前只匹配 `🇸🇬` 新加坡节点并做 `url-test`。
  - 若要增强稳定性，应在该 snippet 中设计回退策略，并检查所有引用该基础片段的 profile。
- `♻️ 自动选择` 目前只保留主流节点：新加坡、日本、香港、美国、中国。
- 引入新的 `[]策略组` 引用时，必须确保该策略组在同一 profile 的最终组合中存在，否则生成脚本会过滤掉该引用。

## 规则顺序

ruleset 顺序会影响命中优先级。新增或移动规则时要检查：

- 私有或更精确的规则应放在更通用规则之前。
- `[]GEOIP,CN` 和 `[]FINAL` 通常应保持在基础规则末尾。

## 编码与风格

- 保持 UTF-8。
- 本仓库配置文件大量使用中文和 emoji，编辑时不要移除既有 emoji，除非用户明确要求。
- 新增注释优先使用中文，并与现有片段风格一致。
- 保持片段简单直接，不为未来场景过度抽象。
- 路径和命令示例使用双引号包裹。

## 危险操作

未经用户明确要求，不要执行：

- `git commit`
- `git push`
- `git reset --hard`
- 删除文件或目录
- 批量重命名
- 全局安装或升级依赖

如需执行这些操作，先向用户说明操作类型、影响范围和风险，并等待确认。

## 推荐处理方式

收到需求后先判断变更落点：

- 用户提到某个生成配置问题时，先到 `Snippets/` 找源头。
- 用户提到某个域名、IP、服务分流时，先查 `Ruleset/` 和 `Snippets/ruleset/`。
- 用户提到节点筛选、测速、fallback、select 时，先查 `Snippets/custom_proxy_group/`。
- 用户提到生成顺序或某个配置文件缺少策略组时，先查 `Snippets/profiles.yaml`。

完成修改后，至少检查：

```bash
git diff -- "Snippets" "Ruleset" "Config"
```

如果改动影响生成结果，优先用预览生成确认脚本不报错：

```bash
python3 "Snippets/build_configs.py"
```
