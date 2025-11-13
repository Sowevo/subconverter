import base64
import subprocess
import sys
from copy import deepcopy
from shutil import which
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urlencode

import requests
import yaml
from retrying import retry

HOME_OFFICE_TAG = 'HO'
SHORTENER_ENDPOINT = 'https://v1.mk/short'
# 针对不同使用场景的规则合集，统一维护目标、是否附加自定义规则等信息
PROFILE_RULES = {
    'WORK': {
        'config_key': 'work',
        'append_extend': True,
        'rename_suffix': f"`!!GROUP={HOME_OFFICE_TAG}!!^@[{HOME_OFFICE_TAG}]",
        'target': 'clashr',
    },
    'GENERAL': {
        'config_key': 'general',
        'append_extend': True,
        'rename_suffix': f"`!!GROUP={HOME_OFFICE_TAG}!!^@[{HOME_OFFICE_TAG}]",
        'target': 'clashr',
    },
    'ROUTER': {
        'config_key': 'router',
        'append_extend': False,
        'rename_suffix': None,
        'target': 'clashr',
    },
}


@retry(stop_max_attempt_number=10, wait_fixed=1000)
def get_short_url(url: str) -> str:
    """请求短链服务并返回短链接，如果失败则触发重试。"""
    payload = {'longUrl': base64.b64encode(url.encode('utf-8'))}
    response = requests.post(SHORTENER_ENDPOINT, data=payload, timeout=10)
    response.raise_for_status()
    try:
        return response.json()['ShortUrl']
    except (KeyError, ValueError) as exc:
        raise ValueError("<!--获取短连接失败-->") from exc


def load_config(path: str = 'subconverter.yaml') -> Dict[str, Any]:
    """从 YAML 配置中装载所有机场以及全局参数。"""
    with open(path, 'r', encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def merge_params(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """生成服务级参数，服务内的配置覆盖全局配置。"""
    merged = deepcopy(defaults)
    merged.update(overrides)
    return merged


def build_profile_param(
    service_name: str,
    base_param: Dict[str, Any],
    profile_key: str,
    extend_url: str,
    config_files: Dict[str, str],
) -> Dict[str, Any]:
    """根据不同类型的 profile 生成最终的请求参数。"""
    rules = PROFILE_RULES[profile_key]
    param = base_param.copy()
    param['target'] = rules['target']

    if rules['append_extend']:
        param['url'] = f"{param['url']}|tag:{HOME_OFFICE_TAG},{extend_url}"

    rename_suffix = rules['rename_suffix']
    if rename_suffix:
        param['rename'] = f"{param['rename']}{rename_suffix}"

    config_key = rules['config_key']
    if config_key not in config_files:
        raise KeyError(f"配置缺少 {config_key} 入口")

    clean_param = param.copy()
    clean_param['config'] = config_files[config_key]
    clean_param['filename'] = f"{service_name}_{profile_key}.yaml"
    return clean_param


def generate_profile_row(service: Dict[str, Any], settings: Dict[str, Any], profile_key: str) -> str:
    base_param = merge_params(settings['defaults'], service['overrides'])
    profile_param = build_profile_param(
        service['name'],
        base_param,
        profile_key,
        settings['extend_url'],
        settings['config_files'],
    )
    url = f"{settings['endpoint']}?{urlencode(profile_param)}"
    short_url = get_short_url(url)
    return f"|[{service['name']}]({service['site']})|{profile_key}|[链接]({url})|{short_url}|"


def add_tag_metadata(service: Dict[str, Any]) -> None:
    """补齐特定机场的 tag、rename 等字段，便于后续筛选。"""
    short_name = service.get('short_name') or service['name'][:2]
    overrides = service.setdefault('overrides', {})
    overrides['url'] = f"tag:{short_name},{overrides.get('url', '')}"
    overrides['rename'] = f"!!GROUP={short_name}!!^@[{short_name}]"


def build_mix_service(services: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """合成一个“混合”机场，聚合被标记为 mix 的订阅。"""
    mix_candidates = [service for service in services if service.get('mix')]
    if not mix_candidates:
        return None

    mix_urls: List[str] = []
    mix_renames: List[str] = []
    mix_excludes: List[str] = []
    mix_param: Dict[str, Any] = {}

    for service in mix_candidates:
        overrides = service.get('overrides', {})
        mix_urls.append(overrides.get('url', ''))
        mix_renames.append(overrides.get('rename', ''))
        mix_excludes.append(overrides.get('exclude', ''))
        mix_param.update(overrides)

    mix_param.update(
        {
            'url': '|'.join(mix_urls),
            'exclude': '|'.join(mix_excludes),
            'rename': '`'.join(mix_renames),
        }
    )
    return {'name': '混合', 'site': 'https://baidu.com', 'overrides': mix_param}


def prepare_services(raw_services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """拷贝配置并注入 tag，必要时追加混合机场。"""
    services = deepcopy(raw_services)
    for service in services:
        add_tag_metadata(service)

    mix_service = build_mix_service(services)
    if mix_service:
        services.append(mix_service)
    return services


def render_table(services: Iterable[Dict[str, Any]], settings: Dict[str, Any]) -> str:
    """按 Markdown 表格输出每个机场的三类链接，并返回完整字符串。"""
    lines = ['| 机场  | 类型 | 链接  | 短连接|', '| :----: | :----: | :----: | :----: |']
    for service in services:
        for profile_key in PROFILE_RULES:
            lines.append(generate_profile_row(service, settings, profile_key))
    table = '\n'.join(lines)
    print(table)
    return table


def copy_to_clipboard(text: str) -> bool:
    """跨平台复制文本到剪贴板，返回复制结果。"""
    commands: List[List[str]]
    if sys.platform.startswith('darwin'):
        commands = [['pbcopy']]
    elif sys.platform.startswith('win'):
        commands = [['clip']]
    else:
        commands = [['xclip', '-selection', 'clipboard'], ['xsel', '--clipboard', '--input']]

    for command in commands:
        if which(command[0]) is None:
            continue
        try:
            subprocess.run(command, input=text.encode('utf-8'), check=True)
            print('✅ 已复制到剪贴板，可直接粘贴。')
            return True
        except (OSError, subprocess.CalledProcessError):
            continue
    print('⚠️ 复制到剪贴板失败，可手动复制以上表格。', file=sys.stderr)
    return False


def main() -> None:
    """脚本入口：读取配置、准备数据、输出表格。"""
    config = load_config()
    settings = config['subconverter']
    services = prepare_services(config['services'])
    table = render_table(services, settings)
    copy_to_clipboard(table)


if __name__ == '__main__':
    main()
