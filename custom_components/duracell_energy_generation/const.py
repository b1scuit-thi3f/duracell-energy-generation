from __future__ import annotations

DOMAIN = "duracell_energy_generation"

CONF_MEMBER_ID = "member_id"
CONF_PASSWORD = "password"
CONF_MEMBER_AUTO_ID = "member_auto_id"

CONF_GOODS_ID = "goods_id"
CONF_INVERTER_NAME = "inverter_name"
CONF_INVERTER_AUTO_ID = "inverter_auto_id"

DEFAULT_SCAN_INTERVAL_SECONDS = 60

BASE_API_ROOT = (
    "https://monitoring.duracellenergy.com/dist/server/api/CodeIgniter/index.php"
)

INVERTER_API_PATH = "Senergytec/web/v2/Inverterapi"
IOT_API_PATH = "Aliyuniotapi/iot"

SIGN_ONE = "05469137076236813460585715952089"
SIGN_TWO = "5161557162012237"