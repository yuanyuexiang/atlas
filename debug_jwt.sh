#!/bin/bash
# JWT 配置调试脚本

echo "========================================="
echo "JWT 配置调试"
echo "========================================="
echo ""

# 1. 检查本地配置
echo "1️⃣  本地配置:"
cd /Users/yuanyuexiang/Desktop/workspace/atlas
.venv/bin/python -c "
from core.auth_config import auth_settings
import hashlib
print(f'  Secret Key MD5: {hashlib.md5(auth_settings.secret_key.encode()).hexdigest()}')
print(f'  Secret Key Length: {len(auth_settings.secret_key)}')
print(f'  Algorithm: {auth_settings.algorithm}')
"
echo ""

# 2. 云上登录获取 token
echo "2️⃣  云上登录并获取 token:"
CLOUD_TOKEN=$(curl -k -s -X POST https://atlas.matrix-net.tech/atlas/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

if [ -z "$CLOUD_TOKEN" ]; then
    echo "  ❌ 登录失败"
    exit 1
fi

echo "  ✅ Token 获取成功"
echo "  Token (前40字符): ${CLOUD_TOKEN:0:40}..."
echo ""

# 3. 用本地密钥验证云上 token
echo "3️⃣  用本地密钥验证云上 token:"
.venv/bin/python -c "
from jose import jwt, JWTError
from core.auth_config import auth_settings

token = '$CLOUD_TOKEN'
try:
    payload = jwt.decode(token, auth_settings.secret_key, algorithms=[auth_settings.algorithm])
    print('  ✅ 验证成功 - 密钥一致!')
    print(f'  用户: {payload.get(\"sub\")}')
except JWTError as e:
    print('  ❌ 验证失败 - 密钥不一致!')
    print(f'  错误: {e}')
"
echo ""

# 4. 测试云上 API
echo "4️⃣  测试云上 API 访问:"
RESULT=$(curl -k -s https://atlas.matrix-net.tech/atlas/api/auth/me \
  -H "Authorization: Bearer $CLOUD_TOKEN")

if echo "$RESULT" | grep -q "username"; then
    echo "  ✅ API 调用成功"
    echo "$RESULT" | python3 -m json.tool
else
    echo "  ❌ API 调用失败"
    echo "  $RESULT"
fi
echo ""

# 5. 建议
echo "========================================="
echo "💡 问题排查建议:"
echo "========================================="
echo ""
echo "如果步骤3显示'密钥不一致'，需要:"
echo "1. 检查云上容器的环境变量:"
echo "   docker exec atlas env | grep JWT"
echo ""
echo "2. 重新部署并确保环境变量生效:"
echo "   docker-compose down"
echo "   docker-compose pull"
echo "   docker-compose up -d"
echo ""
echo "3. 查看容器日志:"
echo "   docker-compose logs -f atlas"
echo ""
