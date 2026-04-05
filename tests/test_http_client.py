"""
测试HTTP客户端与本地测试服务器的通信
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gzip
import io
from src.utils.http_client import create_live_server_client
from src.utils.rule_request_builder import RuleRequestBuilder


def test_po_input():
    """测试PO输入接口"""
    print("\n=== 测试PO输入接口 ===")
    
    # 创建客户端
    client = create_live_server_client(
        base_url="http://localhost:8080",
        token="test_token"
    )
    
    try:
        # 测试获取PO输入数据
        input_data = client.get_input_data(
            airline="F8",
            url_path="/api/orengine/po/comptxt",
            data="1234"
        )
        
        print(f"获取PO输入数据成功，数据大小: {len(input_data)} 字节")
        print(f"是否为gzip数据: {input_data.startswith(b'\\x1f\\x8b')}")
        
        # 解压缩数据
        if input_data.startswith(b'\\x1f\\x8b'):
            with gzip.GzipFile(fileobj=io.BytesIO(input_data)) as f:
                decompressed_data = f.read()
            print(f"解压缩后的数据: {decompressed_data}")
            
    except Exception as e:
        print(f"测试PO输入接口失败: {str(e)}")
    finally:
        client.close()


def test_po_output():
    """测试PO输出接口"""
    print("\n=== 测试PO输出接口 ===")
    
    # 创建客户端
    client = create_live_server_client(
        base_url="http://localhost:8080",
        token="test_token"
    )
    
    try:
        # 创建测试gzip数据
        test_data = b"Test PO output data"
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='w') as f:
            f.write(test_data)
        compressed_data = buffer.getvalue()
        
        # 测试提交PO输出数据
        success = client.submit_output_data(
            airline="F8",
            url_path="/api/orengine/po/solution",
            data=compressed_data
        )
        
        if success:
            print("提交PO输出数据成功")
        else:
            print("提交PO输出数据失败")
            
    except Exception as e:
        print(f"测试PO输出接口失败: {str(e)}")
    finally:
        client.close()


def test_ro_input():
    """测试RO输入接口"""
    print("\n=== 测试RO输入接口 ===")
    
    # 创建客户端
    client = create_live_server_client(
        base_url="http://localhost:8080",
        token="test_token"
    )
    
    try:
        # 测试获取RO输入数据
        input_data = client.get_input_data(
            airline="F8",
            url_path="/api/orengine/ro/comptxt",
            data="5678"
        )
        
        print(f"获取RO输入数据成功，数据大小: {len(input_data)} 字节")
        print(f"是否为gzip数据: {input_data.startswith(b'\\x1f\\x8b')}")
        
        # 解压缩数据
        if input_data.startswith(b'\\x1f\\x8b'):
            with gzip.GzipFile(fileobj=io.BytesIO(input_data)) as f:
                decompressed_data = f.read()
            print(f"解压缩后的数据: {decompressed_data}")
            
    except Exception as e:
        print(f"测试RO输入接口失败: {str(e)}")
    finally:
        client.close()


def test_ro_output():
    """测试RO输出接口"""
    print("\n=== 测试RO输出接口 ===")
    
    # 创建客户端
    client = create_live_server_client(
        base_url="http://localhost:8080",
        token="test_token"
    )
    
    try:
        # 创建测试gzip数据
        test_data = b"Test RO output data"
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='w') as f:
            f.write(test_data)
        compressed_data = buffer.getvalue()
        
        # 测试提交RO输出数据
        success = client.submit_output_data(
            airline="F8",
            url_path="/api/orengine/ro/solution",
            data=compressed_data
        )
        
        if success:
            print("提交RO输出数据成功")
        else:
            print("提交RO输出数据失败")
            
    except Exception as e:
        print(f"测试RO输出接口失败: {str(e)}")
    finally:
        client.close()


def test_change_flight():
    """测试change_flight接口"""
    print("\n=== 测试change_flight接口 ===")
    
    # 创建客户端
    client = create_live_server_client(
        base_url="http://localhost:8080",
        token="test_token"
    )
    
    try:
        # 构建请求数据
        parameters = {
            "airline": "BR",
            "division": "P",
            "fltId": "162906,162218,162905"
        }
        request_data = RuleRequestBuilder.build_request("change_flight", parameters)
        
        print(f"构建的请求数据: {request_data}")
        
        # 测试获取输入数据
        input_data = client.get_input_data(
            airline="BR",
            url_path="/api/orengine/byFlight/comptxt",
            data=request_data
        )
        
        print(f"获取change_flight输入数据成功，数据大小: {len(input_data)} 字节")
        
        # 测试提交输出数据
        test_data = b"Test change_flight output data"
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='w') as f:
            f.write(test_data)
        compressed_data = buffer.getvalue()
        
        success = client.submit_output_data(
            airline="BR",
            url_path="/api/orengine/byFlight/save/csv",
            data=compressed_data
        )
        
        if success:
            print("提交change_flight输出数据成功")
        else:
            print("提交change_flight输出数据失败")
            
    except Exception as e:
        print(f"测试change_flight接口失败: {str(e)}")
    finally:
        client.close()


def test_manday():
    """测试manday接口"""
    print("\n=== 测试manday接口 ===")
    
    # 创建客户端
    client = create_live_server_client(
        base_url="http://localhost:8080",
        token="test_token"
    )
    
    try:
        # 构建请求数据
        parameters = {
            "startDt": "2025-02-01",
            "endDt": "2025-03-30",
            "division": "P"
        }
        request_data = RuleRequestBuilder.build_request("manday", parameters)
        
        print(f"构建的请求数据: {request_data}")
        
        # 测试获取输入数据
        input_data = client.get_input_data(
            airline="BR",
            url_path="/api/orengine/ro/partial/comptxt",
            data=request_data
        )
        
        print(f"获取manday输入数据成功，数据大小: {len(input_data)} 字节")
        
        # 测试提交输出数据
        test_data = b"Test manday output data"
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='w') as f:
            f.write(test_data)
        compressed_data = buffer.getvalue()
        
        success = client.submit_output_data(
            airline="BR",
            url_path="/api/crewMandayFd/partlySave/csv/comp",
            data=compressed_data
        )
        
        if success:
            print("提交manday输出数据成功")
        else:
            print("提交manday输出数据失败")
            
    except Exception as e:
        print(f"测试manday接口失败: {str(e)}")
    finally:
        client.close()


def test_manday_byCrew():
    """测试manday_byCrew接口"""
    print("\n=== 测试manday_byCrew接口 ===")
    
    # 创建客户端
    client = create_live_server_client(
        base_url="http://localhost:8080",
        token="test_token"
    )
    
    try:
        # 构建请求数据
        parameters = {
            "startDt": "2024-09-12",
            "endDt": "2024-09-30",
            "division": "P",
            "crewIds": "I73313,H47887,I73647,E53500"
        }
        request_data = RuleRequestBuilder.build_request("manday_byCrew", parameters)
        
        print(f"构建的请求数据: {request_data}")
        
        # 测试获取输入数据
        input_data = client.get_input_data(
            airline="BR",
            url_path="/api/orengine/byCrew/comptxt",
            data=request_data
        )
        
        print(f"获取manday_byCrew输入数据成功，数据大小: {len(input_data)} 字节")
        
        # 测试提交输出数据
        test_data = b"Test manday_byCrew output data"
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='w') as f:
            f.write(test_data)
        compressed_data = buffer.getvalue()
        
        success = client.submit_output_data(
            airline="BR",
            url_path="/api/crewMandayFd/partlySave/csv/comp",
            data=compressed_data
        )
        
        if success:
            print("提交manday_byCrew输出数据成功")
        else:
            print("提交manday_byCrew输出数据失败")
            
    except Exception as e:
        print(f"测试manday_byCrew接口失败: {str(e)}")
    finally:
        client.close()


if __name__ == "__main__":
    print("开始测试HTTP客户端与本地测试服务器的通信...")
    
    # 测试PO接口
    test_po_input()
    test_po_output()
    
    # 测试RO接口
    test_ro_input()
    test_ro_output()
    
    # 测试Rule接口
    test_change_flight()
    test_manday()
    test_manday_byCrew()
    
    print("\n测试完成！")
