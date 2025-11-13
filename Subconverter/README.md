# Subconverter Helper

生成多个机场的订阅表格，自动附加自定义规则、调用短链服务并复制结果到剪贴板，方便快速分享。

## 功能
- 读取 `subconverter.yaml`，对每个机场生成 `WORK`/`GENERAL`/`ROUTER` 三类订阅。
- 支持按 `mix` 标识生成一个“混合”订阅，将多个机场合并。
- 调用 `https://v1.mk/short` 生成短链接，输出 Markdown 表格。
- 输出完成后尝试自动复制表格到系统剪贴板（macOS `pbcopy`、Windows `clip`、Linux `xclip/xsel`）。

## 依赖
```bash
pip install -r requirements.txt
```

## 使用
```bash
python subconverter.py
```
终端会打印 Markdown 表格；若系统支持剪贴板命令会提示 `✅ 已复制到剪贴板`。

## 配置说明
- `subconverter.yaml`：主配置文件，包含全局 `subconverter` 设置以及 `services` 列表。
  - `subconverter.endpoint`：Subconverter 服务地址。
  - `extend_url`：需要拼接的额外订阅。
  - `config_files`：不同 profile 对应的规则文件 URL。
  - `defaults`：默认参数，可被单个机场 `overrides` 覆盖。
- `services`：每个机场的基础信息与个性化参数。
  - `mix: true` 会被纳入混合订阅。
  - `short_name` 用于自动生成 tag/rename。
  - `overrides` 覆盖默认参数，例如订阅 `url`、`exclude` 等。

参考 `subconverter_example.yaml` 快速创建自己的配置。
