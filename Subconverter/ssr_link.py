import base64
import re
from urllib.parse import urlparse, parse_qs, urlencode


def decode_ssr(ssr_url):
    """解析 SSR 链接为字典"""
    # 移除协议头并解码 Base64
    encoded = ssr_url[6:]
    padded = encoded + '=' * (4 - len(encoded) % 4)
    decoded = base64.urlsafe_b64decode(padded).decode('utf-8')

    # 提取基础信息
    pattern = r'^([^:]+):(\d+):([^:]*):([^:]+):([^:]*):([^/?]+)'
    match = re.match(pattern, decoded)
    if not match:
        raise ValueError("Invalid SSR link format")

    server, port, protocol, method, obfs, password_b64 = match.groups()

    # 解码密码
    password = base64.urlsafe_b64decode(password_b64 + '==').decode('utf-8')

    # 提取查询参数
    params = {}
    if '?' in decoded:
        query_str = decoded.split('?', 1)[1]
        query_params = parse_qs(query_str)
        for key, values in query_params.items():
            # 特殊处理 remarks 参数
            if key == 'remarks':
                params[key] = base64.urlsafe_b64decode(values[0] + '==').decode('utf-8')
            else:
                params[key] = values[0]

    return {
        'server': server,
        'port': int(port),
        'protocol': protocol,
        'method': method,
        'obfs': obfs,
        'password': password,
        'params': params
    }


def encode_ssr(config):
    """将配置字典编码为 SSR 链接"""
    # 编码密码
    password_b64 = base64.urlsafe_b64encode(
        config['password'].encode('utf-8')
    ).decode('utf-8').rstrip('=')

    # 构建基础部分
    base_str = f"{config['server']}:{config['port']}:{config['protocol']}:" \
               f"{config['method']}:{config['obfs']}:{password_b64}"

    # 处理查询参数
    params = config.get('params', {})
    query_params = {}
    for key, value in params.items():
        # 特殊处理 remarks 参数
        if key == 'remarks':
            query_params[key] = base64.urlsafe_b64encode(
                value.encode('utf-8')
            ).decode('utf-8').rstrip('=')
        else:
            query_params[key] = value

    # 组合完整字符串
    if query_params:
        query_str = urlencode(query_params, doseq=True)
        full_str = f"{base_str}/?{query_str}"
    else:
        full_str = base_str

    # Base64 编码
    return "ssr://" + base64.urlsafe_b64encode(
        full_str.encode('utf-8')
    ).decode('utf-8').rstrip('=')


# 示例使用
if __name__ == "__main__":
    # 创建配置字典，只包含指定参数
    config = {
        'server': 'ss.example.com',
        'port': 10086,
        'protocol': 'origin',  # 设置为默认值
        'method': 'aes-128-cfb',  # cipher参数
        'obfs': 'plain',  # 设置为默认值
        'password': 'pAsswOrd',
        'params': {
            'remarks': '🇨🇳 名字'  # name参数
        }
    }

    # 1. 先调用 encode_ssr 生成链接
    generated_ssr = encode_ssr(config)
    print("生成的 SSR 链接:")
    print(generated_ssr)

    # 2. 再调用 decode_ssr 解析链接
    parsed_config = decode_ssr(generated_ssr)

    print("\n解析结果:")
    print(f"服务器: {parsed_config['server']}")
    print(f"端口: {parsed_config['port']}")
    print(f"协议: {parsed_config['protocol']} (默认值)")
    print(f"加密方法: {parsed_config['method']}")
    print(f"混淆: {parsed_config['obfs']} (默认值)")
    print(f"密码: {parsed_config['password']}")
    print(f"备注: {parsed_config['params'].get('remarks', '')}")

    # 验证配置是否一致
    print("\n验证结果:")
    print("服务器匹配:", config['server'] == parsed_config['server'])
    print("端口匹配:", config['port'] == parsed_config['port'])
    print("加密方法匹配:", config['method'] == parsed_config['method'])
    print("密码匹配:", config['password'] == parsed_config['password'])
    print("备注匹配:", config['params']['remarks'] == parsed_config['params']['remarks'])