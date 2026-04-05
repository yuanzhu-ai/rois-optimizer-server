"""
本地测试Live Server，用于模拟真实Live Server的行为
"""
import http.server
import socketserver
import json
import gzip
import io
import logging
from urllib.parse import urlparse, parse_qs

# 配置日志
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class LiveServerHandler(http.server.BaseHTTPRequestHandler):
    """Live Server请求处理器"""
    
    def do_POST(self):
        """处理POST请求"""
        # 获取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        # 记录请求信息
        logger.info(f"收到POST请求: {self.path}")
        logger.info(f"请求头: {dict(self.headers)}")
        
        try:
            # 解析请求路径
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            # 处理不同的接口
            if '/api/orengine/po/comptxt' in path:
                self._handle_po_comptxt(body)
            elif '/api/orengine/po/solution' in path:
                self._handle_po_solution(body)
            elif '/api/orengine/ro/comptxt' in path:
                self._handle_ro_comptxt(body)
            elif '/api/orengine/ro/solution' in path:
                self._handle_ro_solution(body)
            elif '/api/orengine/byFlight/comptxt' in path:
                self._handle_by_flight_comptxt(body)
            elif '/api/orengine/byFlight/save/csv' in path:
                self._handle_by_flight_save(body)
            elif '/api/orengine/ro/partial/comptxt' in path:
                self._handle_ro_partial_comptxt(body)
            elif '/api/crewMandayFd/partlySave/csv/comp' in path:
                self._handle_crew_manday_save(body)
            elif '/api/orengine/byCrew/comptxt' in path:
                self._handle_by_crew_comptxt(body)
            else:
                self._handle_not_found()
                
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}")
            self._send_error(500, f"服务器内部错误: {str(e)}")
    
    def _handle_po_comptxt(self, body):
        """处理PO输入请求"""
        logger.info(f"PO输入请求体: {body.decode('utf-8')}")
        
        # 模拟返回gzip压缩的数据
        response_data = b"Mock PO input data"
        compressed_data = self._gzip_compress(response_data)
        
        self._send_response(200, compressed_data, {
            'Content-Type': 'application/octet-stream',
            'Content-Encoding': 'gzip'
        })
    
    def _handle_po_solution(self, body):
        """处理PO输出请求"""
        logger.info(f"PO输出请求体大小: {len(body)} 字节")
        logger.info(f"是否为gzip数据: {body.startswith(b'\x1f\x8b')}")
        
        # 模拟成功响应
        self._send_response(200, b"OK")
    
    def _handle_ro_comptxt(self, body):
        """处理RO输入请求"""
        logger.info(f"RO输入请求体: {body.decode('utf-8')}")
        
        # 模拟返回gzip压缩的数据
        response_data = b"Mock RO input data"
        compressed_data = self._gzip_compress(response_data)
        
        self._send_response(200, compressed_data, {
            'Content-Type': 'application/octet-stream',
            'Content-Encoding': 'gzip'
        })
    
    def _handle_ro_solution(self, body):
        """处理RO输出请求"""
        logger.info(f"RO输出请求体大小: {len(body)} 字节")
        logger.info(f"是否为gzip数据: {body.startswith(b'\x1f\x8b')}")
        
        # 模拟成功响应
        self._send_response(200, b"OK")
    
    def _handle_by_flight_comptxt(self, body):
        """处理change_flight输入请求"""
        logger.info(f"change_flight输入请求体: {body.decode('utf-8')}")
        
        # 解析JSON
        try:
            data = json.loads(body)
            logger.info(f"解析后的change_flight数据: {data}")
        except json.JSONDecodeError:
            logger.error("无法解析JSON数据")
        
        # 模拟返回gzip压缩的数据
        response_data = b"Mock change_flight input data"
        compressed_data = self._gzip_compress(response_data)
        
        self._send_response(200, compressed_data, {
            'Content-Type': 'application/octet-stream',
            'Content-Encoding': 'gzip'
        })
    
    def _handle_by_flight_save(self, body):
        """处理change_flight输出请求"""
        logger.info(f"change_flight输出请求体大小: {len(body)} 字节")
        logger.info(f"是否为gzip数据: {body.startswith(b'\x1f\x8b')}")
        
        # 模拟成功响应
        self._send_response(200, b"OK")
    
    def _handle_ro_partial_comptxt(self, body):
        """处理manday输入请求"""
        logger.info(f"manday输入请求体: {body.decode('utf-8')}")
        
        # 解析JSON
        try:
            data = json.loads(body)
            logger.info(f"解析后的manday数据: {data}")
        except json.JSONDecodeError:
            logger.error("无法解析JSON数据")
        
        # 模拟返回gzip压缩的数据
        response_data = b"Mock manday input data"
        compressed_data = self._gzip_compress(response_data)
        
        self._send_response(200, compressed_data, {
            'Content-Type': 'application/octet-stream',
            'Content-Encoding': 'gzip'
        })
    
    def _handle_crew_manday_save(self, body):
        """处理manday输出请求"""
        logger.info(f"manday输出请求体大小: {len(body)} 字节")
        logger.info(f"是否为gzip数据: {body.startswith(b'\x1f\x8b')}")
        
        # 模拟成功响应
        self._send_response(200, b"OK")
    
    def _handle_by_crew_comptxt(self, body):
        """处理manday_byCrew输入请求"""
        logger.info(f"manday_byCrew输入请求体: {body.decode('utf-8')}")
        
        # 解析JSON
        try:
            data = json.loads(body)
            logger.info(f"解析后的manday_byCrew数据: {data}")
        except json.JSONDecodeError:
            logger.error("无法解析JSON数据")
        
        # 模拟返回gzip压缩的数据
        response_data = b"Mock manday_byCrew input data"
        compressed_data = self._gzip_compress(response_data)
        
        self._send_response(200, compressed_data, {
            'Content-Type': 'application/octet-stream',
            'Content-Encoding': 'gzip'
        })
    
    def _handle_not_found(self):
        """处理未找到的接口"""
        self._send_error(404, "接口未找到")
    
    def _send_response(self, status_code, data, headers=None):
        """发送响应"""
        self.send_response(status_code)
        
        # 设置默认响应头
        default_headers = {
            'Content-Type': 'text/plain',
            'Content-Length': len(data)
        }
        
        # 更新响应头
        if headers:
            default_headers.update(headers)
        
        # 发送响应头
        for key, value in default_headers.items():
            self.send_header(key, value)
        self.end_headers()
        
        # 发送响应体
        self.wfile.write(data)
    
    def _send_error(self, status_code, message):
        """发送错误响应"""
        error_data = message.encode('utf-8')
        self._send_response(status_code, error_data, {
            'Content-Type': 'text/plain'
        })
    
    def _gzip_compress(self, data):
        """压缩数据为gzip格式"""
        buffer = io.BytesIO()
        with gzip.GzipFile(fileobj=buffer, mode='w') as f:
            f.write(data)
        return buffer.getvalue()

def start_test_server(host='localhost', port=8080):
    """启动测试服务器"""
    logger.info(f"启动测试Live Server在 {host}:{port}")
    
    # 创建服务器
    handler = LiveServerHandler
    httpd = socketserver.TCPServer((host, port), handler)
    
    try:
        # 启动服务器
        logger.info("测试Live Server已启动，按Ctrl+C停止")
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("正在停止测试Live Server...")
        httpd.shutdown()
        logger.info("测试Live Server已停止")

if __name__ == "__main__":
    start_test_server()
