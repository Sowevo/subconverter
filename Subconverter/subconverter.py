import yaml
import base64
import requests
from urllib.parse import urlencode
from retrying import retry


# 重试装饰器
@retry(stop_max_attempt_number=10, wait_fixed=1000)
def get_short_url(url):
    payload = {'longUrl': base64.b64encode(url.encode("utf-8"))}
    response = requests.request("POST", 'https://v1.mk/short', data=payload)
    try:
        url = response.json()['ShortUrl']
        return url
    except Exception:
        raise Exception("<!--获取短连接失败-->")


def get_config():
    with open("subconverter.yaml", "r") as stream:
        data = yaml.safe_load(stream)
        return data


def get_param(service_subconverter, subconverter):
    # 定义一个参数字典,先加入全局参数,再加入个性化参数,重复的覆盖
    param = {**subconverter, **service_subconverter}
    return param


# 生成URL的函数
def generate_url(service, config, _type):
    extend_url = config['extend_url']
    subconverter_url = config['subconverter_url']
    # 非全局配置
    subconverter = config['subconverter']
    # 通用配置
    service_subconverter = service['subconverter']
    name = service['name']
    site = service['site']
    param = get_param(service_subconverter, subconverter)
    if _type == 'WORK':
        param['target'] = 'clashr'
        param['url'] = param['url'] + '|tag:HO,' + extend_url
        param['rename'] = param['rename'] + '`!!GROUP=HO!!^@[HO]'
        param['config'] = subconverter['config_file']['work']
    elif _type == 'GENERAL':
        param['target'] = 'clashr'
        param['url'] = param['url'] + '|tag:HO,' + extend_url
        param['rename'] = param['rename'] + '`!!GROUP=HO!!^@[HO]'
        param['config'] = subconverter['config_file']['general']
    elif _type == 'ROUTER':
        param['target'] = 'clashr'
        param['config'] = subconverter['config_file']['router']
    param['filename'] = f"{name}_{_type}.yaml"
    url = subconverter_url + '?' + urlencode(param)
    short_url = get_short_url(url)
    return f"|[{name}]({site})|{_type}|[链接]({url})|{short_url}|"


# 主要执行部分
config = get_config()
services = config['services']

# 补充tag信息
for service in services:
    short_name = service.get('short_name', service['name'][0:2])
    service['subconverter']['url'] = f"tag:{short_name},{service['subconverter']['url']}"
    service['subconverter']['rename'] = f"!!GROUP={short_name}!!^@[{short_name}]"

mix_urls = []
mix_renames = []
mix_exclude = []
mix_param = {}

# 找出需要混合的
for service in services:
    if service['mix']:
        subconverter = service['subconverter']
        mix_urls.append(subconverter.get('url', ''))
        mix_renames.append(subconverter.get('rename', ''))
        mix_exclude.append(subconverter.get('exclude', ''))
        # 加入通用配置
        mix_param.update(service['subconverter'])

if len(mix_urls):
    mix_param.update({'url': '|'.join(mix_urls), 'exclude': '|'.join(mix_exclude), 'rename': '`'.join(mix_renames)})
    mix_service = {'name': '混合', 'site': 'https://baidu.com', 'subconverter': mix_param}
    services.append(mix_service)

print('| 机场  | 类型 | 链接  | 短连接|')
print('| :----: | :----: | :----: | :----: |')
for service in services:
    # 生成公司用的订阅链接 -->> 包含回家规则与公司屏蔽服务规则
    work_url = generate_url(service, config, 'WORK')
    print(work_url)
    # 生成通用的订阅链接 -->> 包含回家规则
    general_url = generate_url(service, config, 'GENERAL')
    print(general_url)
    # 生成软路由的订阅链接
    router_url = generate_url(service, config, 'ROUTER')
    print(router_url)

