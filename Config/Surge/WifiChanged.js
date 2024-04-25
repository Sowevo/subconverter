// Surge根据Wifi自动切换代理的脚本

// 不需要代理的WIFI名称
const WIFI_DONT_NEED_PROXYS = ['RUOK_5G','RUOK'];
// 当前WIFI名称存储的key
const CURRENT_WIFI_SSID_KEY = 'current_wifi_ssid';

if (wifiChanged()) {
    setOutboundMode();
}

function setOutboundMode(){
    const mode = WIFI_DONT_NEED_PROXYS.includes($network.wifi.ssid) ? 'direct' : 'rule';
    $surge.setOutboundMode(mode);
    $notification.post(
        'Surge',
        `网络切换为 ${$network.wifi.ssid || '蜂窝'}`,
        `使用 ${mode === 'direct' ? '直接链接':'规则模式' }`
    );
}

function wifiChanged() {
    const currentWifiSSid = $persistentStore.read(CURRENT_WIFI_SSID_KEY);
    const changed = currentWifiSSid !== $network.wifi.ssid;
    changed && $persistentStore.write($network.wifi.ssid, CURRENT_WIFI_SSID_KEY);
    return changed;
}

$done();
