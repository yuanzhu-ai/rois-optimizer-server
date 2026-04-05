#!/usr/bin/env python3
"""
直接测试Live Server的RO接口
"""
import requests

url = 'http://localhost/api/orengine/ro/comptxt'
headers = {
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.eyIwIjoxLCJpc3MiOiJhZG1pbkBwaS1zb2x1dGlvbiIsImV4cCI6MTc3NTMxNTU4OSwidXNlck5hbWUiOiJ5dWFuLnoifQ.Pk17CJ8Z_alUXwy37UoGoCqabgTK_yOddsr309LdLu8',
    'Content-Type': 'application/json'
}
data = 3739

print(f'请求URL: {url}')
print(f'请求数据: {data}')
print(f'请求头: {headers}')
print()

try:
    response = requests.post(url, headers=headers, json=data, timeout=300)
    print(f'状态码: {response.status_code}')
    print(f'Content-Type: {response.headers.get("Content-Type")}')
    print(f'数据大小: {len(response.content)} bytes')
    
    if response.status_code == 200:
        with open('test_ro_direct.gz', 'wb') as f:
            f.write(response.content)
        print('数据已保存到 test_ro_direct.gz')
    else:
        print(f'响应: {response.text[:500]}')
except Exception as e:
    print(f'错误: {e}')
