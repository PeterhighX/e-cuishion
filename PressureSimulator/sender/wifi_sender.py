"""
WiFi数据发送器
模拟ESP32通过TCP发送压力数据到WiReSensPy系统
"""

import socket
import time
import threading
import logging
from typing import List, Optional, Dict, Any
import numpy as np

from .protocol_handler import WifiProtocolHandler

class WifiSender:
    """WiFi TCP数据发送器"""
    
    def __init__(self, target_ip: str = "10.0.0.67", target_port: int = 7000,
                 sensor_id: int = 1, nodes_per_packet: int = 256):
        """
        初始化WiFi发送器
        
        Args:
            target_ip: 目标IP地址（WiReSensPy服务器）
            target_port: 目标端口
            sensor_id: 传感器ID
            nodes_per_packet: 每包节点数
        """
        self.target_ip = target_ip
        self.target_port = target_port
        self.sensor_id = sensor_id
        self.nodes_per_packet = nodes_per_packet
        
        # 协议处理器
        self.protocol_handler = WifiProtocolHandler(nodes_per_packet)
        
        # 连接状态
        self.socket = None
        self.connected = False
        self.running = False
        
        # 统计信息
        self.packets_sent = 0
        self.frames_sent = 0
        self.bytes_sent = 0
        self.start_time = None
        
        # 发送参数
        self.frame_rate = 30  # 帧率
        self.packet_delay = 0.001  # 包间延迟（秒）
        
        # 日志
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f'WifiSender_{self.sensor_id}')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def connect(self, timeout: float = 10.0) -> bool:
        """
        连接到目标服务器
        
        Args:
            timeout: 连接超时时间
            
        Returns:
            连接是否成功
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(timeout)
            
            self.logger.info(f"连接到 {self.target_ip}:{self.target_port}...")
            self.socket.connect((self.target_ip, self.target_port))
            
            self.connected = True
            self.logger.info("连接成功")
            
            # 发送传感器ID标识
            self._send_sensor_identification()
            
            return True
            
        except socket.timeout:
            self.logger.error(f"连接超时: {self.target_ip}:{self.target_port}")
            return False
        except socket.error as e:
            self.logger.error(f"连接失败: {e}")
            return False
        except Exception as e:
            self.logger.error(f"连接时发生未知错误: {e}")
            return False
    
    def _send_sensor_identification(self):
        """发送传感器身份标识（模拟真实传感器的握手过程）"""
        try:
            # 发送一个标识数据包，让服务器知道这是哪个传感器
            dummy_readings = [0] * self.nodes_per_packet
            id_packet = self.protocol_handler.encode_packet(
                self.sensor_id, 0, dummy_readings, 0
            )
            self.socket.send(id_packet)
            self.logger.info(f"已发送传感器ID标识: {self.sensor_id}")
        except Exception as e:
            self.logger.warning(f"发送传感器ID标识失败: {e}")
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
                self.logger.info("连接已断开")
            except Exception as e:
                self.logger.error(f"断开连接时发生错误: {e}")
            finally:
                self.socket = None
        
        self.connected = False
    
    def send_frame(self, pressure_data: np.ndarray) -> bool:
        """
        发送一帧压力数据（1024个节点，分4个包）
        
        Args:
            pressure_data: 1024长度的压力数据或32*32的2D数组
            
        Returns:
            发送是否成功
        """
        if not self.connected or not self.socket:
            self.logger.error("未连接到服务器")
            return False
        
        try:
            # 确保数据是1D格式
            if pressure_data.ndim == 2:
                pressure_1d = pressure_data.flatten()
            else:
                pressure_1d = pressure_data
            
            if len(pressure_1d) != 1024:
                self.logger.error(f"压力数据长度错误: {len(pressure_1d)}, 期望1024")
                return False
            
            # 分包并发送
            tcp_packets = self.protocol_handler.prepare_tcp_data(self.sensor_id, pressure_1d)
            
            for i, packet_bytes in enumerate(tcp_packets):
                # 发送数据包
                self.socket.send(packet_bytes)
                self.packets_sent += 1
                self.bytes_sent += len(packet_bytes)
                
                # 包间延迟
                if i < len(tcp_packets) - 1 and self.packet_delay > 0:
                    time.sleep(self.packet_delay)
            
            self.frames_sent += 1
            return True
            
        except socket.error as e:
            self.logger.error(f"发送数据时连接错误: {e}")
            self.connected = False
            return False
        except Exception as e:
            self.logger.error(f"发送数据时发生错误: {e}")
            return False
    
    def send_continuous(self, data_generator, duration: Optional[float] = None):
        """
        持续发送数据
        
        Args:
            data_generator: 数据生成器函数，每次调用返回一帧数据
            duration: 发送持续时间（秒），None表示无限制
        """
        if not self.connected:
            self.logger.error("未连接到服务器")
            return
        
        self.running = True
        self.start_time = time.time()
        
        frame_interval = 1.0 / self.frame_rate
        next_send_time = time.time()
        
        self.logger.info(f"开始持续发送数据，帧率: {self.frame_rate} FPS")
        
        try:
            while self.running:
                current_time = time.time()
                
                # 检查是否需要停止（基于持续时间）
                if duration and (current_time - self.start_time) >= duration:
                    break
                
                # 检查是否到了发送时间
                if current_time >= next_send_time:
                    # 生成并发送数据
                    pressure_data = data_generator()
                    
                    if self.send_frame(pressure_data):
                        next_send_time = current_time + frame_interval
                    else:
                        self.logger.error("发送失败，停止持续发送")
                        break
                
                # 短暂休眠避免CPU占用过高
                time.sleep(0.001)
                
        except KeyboardInterrupt:
            self.logger.info("用户中断，停止发送")
        except Exception as e:
            self.logger.error(f"持续发送时发生错误: {e}")
        finally:
            self.running = False
            self._print_statistics()
    
    def _print_statistics(self):
        """打印发送统计信息"""
        if self.start_time:
            elapsed_time = time.time() - self.start_time
            avg_fps = self.frames_sent / elapsed_time if elapsed_time > 0 else 0
            avg_bandwidth = self.bytes_sent / elapsed_time / 1024 if elapsed_time > 0 else 0  # KB/s
            
            self.logger.info("=== 发送统计 ===")
            self.logger.info(f"发送时间: {elapsed_time:.2f} 秒")
            self.logger.info(f"发送帧数: {self.frames_sent}")
            self.logger.info(f"发送包数: {self.packets_sent}")
            self.logger.info(f"发送字节: {self.bytes_sent}")
            self.logger.info(f"平均帧率: {avg_fps:.2f} FPS")
            self.logger.info(f"平均带宽: {avg_bandwidth:.2f} KB/s")
    
    def test_connection(self) -> bool:
        """
        测试连接状态
        
        Returns:
            连接是否正常
        """
        if not self.connected or not self.socket:
            return False
        
        try:
            # 发送测试数据包
            test_data = np.zeros(1024, dtype=np.uint16)
            return self.send_frame(test_data)
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取发送器状态
        
        Returns:
            状态信息字典
        """
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            'connected': self.connected,
            'running': self.running,
            'target': f"{self.target_ip}:{self.target_port}",
            'sensor_id': self.sensor_id,
            'frames_sent': self.frames_sent,
            'packets_sent': self.packets_sent,
            'bytes_sent': self.bytes_sent,
            'elapsed_time': elapsed_time,
            'frame_rate': self.frame_rate
        }


if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    
    # 添加simulator模块路径
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'simulator'))
    
    try:
        from data_generator import PressureDataGenerator
        
        # 创建数据生成器
        config = {
            'sensor': {'selWires': 32, 'readWires': 32, 'totalNodes': 1024},
            'generation': {'intensity': 0.5, 'noiseLevel': 0.1, 'dataRange': [0, 4095]}
        }
        generator = PressureDataGenerator(config)
        
        # 创建WiFi发送器
        sender = WifiSender(target_ip="127.0.0.1", target_port=7000, sensor_id=1)
        
        print("测试WiFi发送器...")
        print("注意: 请确保WiReSensPy系统在127.0.0.1:7000监听")
        
        # 连接测试
        if sender.connect():
            print("连接成功，开始发送测试数据...")
            
            # 定义数据生成函数
            def generate_test_data():
                return generator.generate_frame('circle', radius=10, intensity=3000)
            
            # 发送10秒测试数据
            sender.send_continuous(generate_test_data, duration=10.0)
        else:
            print("连接失败")
        
        # 断开连接
        sender.disconnect()
        
    except ImportError:
        print("测试需要data_generator模块，请先运行simulator/data_generator.py")
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试时发生错误: {e}") 