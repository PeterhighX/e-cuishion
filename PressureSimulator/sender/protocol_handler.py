"""
数据包协议处理器
按照WiReSensPy格式编码和分包压力数据
"""

import struct
import numpy as np
from typing import List, Tuple, Dict, Any

class ProtocolHandler:
    """数据包协议处理器，兼容WiReSensPy格式"""
    
    def __init__(self, nodes_per_packet: int = 256):
        """
        初始化协议处理器
        
        Args:
            nodes_per_packet: 每个数据包包含的节点数（默认256）
        """
        self.nodes_per_packet = nodes_per_packet
        
        # 数据包格式：'=b' + 'H' * (1+numNodes) + 'I'
        # sendId(1字节) + startIdx(2字节) + sensorReadings[numNodes](2*numNodes字节) + packetNumber(4字节)
        self.packet_size = 1 + (1 + nodes_per_packet) * 2 + 4
        
    def encode_packet(self, sensor_id: int, start_idx: int, 
                     readings: List[int], packet_num: int) -> bytes:
        """
        编码单个数据包
        
        Args:
            sensor_id: 传感器ID (int8_t)
            start_idx: 数据包在压力数组中的起始索引 (uint16_t)
            readings: 传感器读数列表 (uint16_t[])
            packet_num: 数据包编号 (uint32_t)
            
        Returns:
            编码后的字节数据
        """
        # 确保readings长度正确
        if len(readings) != self.nodes_per_packet:
            # 如果不足，用0填充
            if len(readings) < self.nodes_per_packet:
                readings = list(readings) + [0] * (self.nodes_per_packet - len(readings))
            else:
                # 如果超出，截断
                readings = readings[:self.nodes_per_packet]
        
        # 构建格式字符串：'=b' + 'H' * (1+numNodes) + 'I'
        format_string = '=b' + 'H' * (1 + self.nodes_per_packet) + 'I'
        
        # 打包数据：sendId, startIdx, readings..., packetNumber
        try:
            packed_data = struct.pack(format_string, sensor_id, start_idx, *readings, packet_num)
            return packed_data
        except struct.error as e:
            print(f"数据包编码错误: {e}")
            print(f"sensor_id: {sensor_id}, start_idx: {start_idx}, readings_len: {len(readings)}, packet_num: {packet_num}")
            raise
    
    def decode_packet(self, packet_data: bytes) -> Tuple[int, int, List[int], int]:
        """
        解码数据包（用于测试和验证）
        
        Args:
            packet_data: 编码的字节数据
            
        Returns:
            (sensor_id, start_idx, readings, packet_num)
        """
        format_string = '=b' + 'H' * (1 + self.nodes_per_packet) + 'I'
        
        try:
            unpacked_data = struct.unpack(format_string, packet_data)
            sensor_id = unpacked_data[0]
            start_idx = unpacked_data[1]
            readings = list(unpacked_data[2:-1])
            packet_num = unpacked_data[-1]
            
            return sensor_id, start_idx, readings, packet_num
        except struct.error as e:
            print(f"数据包解码错误: {e}")
            raise
    
    def split_pressure_data(self, pressure_1d: np.ndarray, sensor_id: int = 1) -> List[Tuple[bytes, Dict[str, Any]]]:
        """
        将1024节点的压力数据分成多个数据包
        
        Args:
            pressure_1d: 1024长度的1D压力数组
            sensor_id: 传感器ID
            
        Returns:
            [(packet_bytes, packet_info), ...] 列表
        """
        if len(pressure_1d) % self.nodes_per_packet != 0:
            print(f"警告: 压力数据长度({len(pressure_1d)})不是每包节点数({self.nodes_per_packet})的整数倍")
        
        packets = []
        packet_count = 0
        
        for i in range(0, len(pressure_1d), self.nodes_per_packet):
            # 提取当前包的数据
            end_idx = min(i + self.nodes_per_packet, len(pressure_1d))
            packet_readings = pressure_1d[i:end_idx].astype(np.uint16).tolist()
            
            # 编码数据包
            packet_bytes = self.encode_packet(sensor_id, i, packet_readings, packet_count)
            
            # 记录包信息
            packet_info = {
                'sensor_id': sensor_id,
                'start_idx': i,
                'end_idx': end_idx,
                'packet_num': packet_count,
                'data_length': len(packet_readings),
                'packet_size': len(packet_bytes)
            }
            
            packets.append((packet_bytes, packet_info))
            packet_count += 1
        
        return packets
    
    def verify_packet_integrity(self, packet_data: bytes) -> bool:
        """
        验证数据包完整性
        
        Args:
            packet_data: 数据包字节数据
            
        Returns:
            是否完整
        """
        # 检查长度
        if len(packet_data) != self.packet_size:
            print(f"数据包长度错误: 期望{self.packet_size}，实际{len(packet_data)}")
            return False
        
        # 尝试解码
        try:
            sensor_id, start_idx, readings, packet_num = self.decode_packet(packet_data)
            
            # 检查数据范围
            if not (0 <= sensor_id <= 127):  # int8_t范围
                print(f"传感器ID超出范围: {sensor_id}")
                return False
            
            if not (0 <= start_idx <= 65535):  # uint16_t范围
                print(f"起始索引超出范围: {start_idx}")
                return False
            
            if not (0 <= packet_num <= 4294967295):  # uint32_t范围
                print(f"包编号超出范围: {packet_num}")
                return False
            
            # 检查读数范围
            for reading in readings:
                if not (0 <= reading <= 65535):  # uint16_t范围
                    print(f"读数超出范围: {reading}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"数据包验证失败: {e}")
            return False
    
    def get_packet_info(self) -> Dict[str, Any]:
        """
        获取数据包格式信息
        
        Returns:
            包含格式信息的字典
        """
        return {
            'nodes_per_packet': self.nodes_per_packet,
            'packet_size_bytes': self.packet_size,
            'format_string': '=b' + 'H' * (1 + self.nodes_per_packet) + 'I',
            'components': {
                'sensor_id': {'type': 'int8_t', 'size': 1},
                'start_idx': {'type': 'uint16_t', 'size': 2},
                'readings': {'type': f'uint16_t[{self.nodes_per_packet}]', 'size': 2 * self.nodes_per_packet},
                'packet_num': {'type': 'uint32_t', 'size': 4}
            }
        }


class WifiProtocolHandler(ProtocolHandler):
    """WiFi协议处理器，继承基础协议处理器"""
    
    def __init__(self, nodes_per_packet: int = 256):
        super().__init__(nodes_per_packet)
    
    def prepare_tcp_data(self, sensor_id: int, pressure_1d: np.ndarray) -> List[bytes]:
        """
        准备TCP传输的数据包
        
        Args:
            sensor_id: 传感器ID
            pressure_1d: 1024长度的压力数据
            
        Returns:
            准备好的TCP数据包列表
        """
        packets = self.split_pressure_data(pressure_1d, sensor_id)
        tcp_packets = []
        
        for packet_bytes, packet_info in packets:
            tcp_packets.append(packet_bytes)
        
        return tcp_packets


class SerialProtocolHandler(ProtocolHandler):
    """串口协议处理器，继承基础协议处理器"""
    
    def __init__(self, nodes_per_packet: int = 256):
        super().__init__(nodes_per_packet)
    
    def prepare_serial_data(self, sensor_id: int, pressure_1d: np.ndarray) -> List[bytes]:
        """
        准备串口传输的数据包（可能需要添加特殊的帧头/帧尾）
        
        Args:
            sensor_id: 传感器ID
            pressure_1d: 1024长度的压力数据
            
        Returns:
            准备好的串口数据包列表
        """
        packets = self.split_pressure_data(pressure_1d, sensor_id)
        serial_packets = []
        
        for packet_bytes, packet_info in packets:
            # 可以在这里添加串口特定的帧格式
            serial_packets.append(packet_bytes)
        
        return serial_packets


if __name__ == "__main__":
    # 测试代码
    print("测试协议处理器...")
    
    # 创建协议处理器
    handler = ProtocolHandler(256)
    
    # 打印格式信息
    print("数据包格式信息:")
    info = handler.get_packet_info()
    for key, value in info.items():
        print(f"  {key}: {value}")
    
    # 测试单个数据包编码/解码
    print("\n测试单个数据包...")
    test_readings = list(range(256))  # 0-255的测试数据
    packet_bytes = handler.encode_packet(1, 0, test_readings, 0)
    print(f"编码后数据包大小: {len(packet_bytes)} 字节")
    
    # 解码测试
    decoded_id, decoded_start, decoded_readings, decoded_packet = handler.decode_packet(packet_bytes)
    print(f"解码结果: ID={decoded_id}, Start={decoded_start}, Packet={decoded_packet}")
    print(f"读数匹配: {decoded_readings == test_readings}")
    
    # 验证完整性
    print(f"数据包完整性: {handler.verify_packet_integrity(packet_bytes)}")
    
    # 测试1024节点数据分包
    print("\n测试1024节点数据分包...")
    test_pressure = np.random.randint(0, 4096, 1024, dtype=np.uint16)
    packets = handler.split_pressure_data(test_pressure, sensor_id=1)
    
    print(f"生成数据包数量: {len(packets)}")
    for i, (packet_bytes, packet_info) in enumerate(packets):
        print(f"  包{i}: {packet_info}")
        
    # 验证所有包
    all_valid = all(handler.verify_packet_integrity(packet_bytes) for packet_bytes, _ in packets)
    print(f"所有数据包都有效: {all_valid}") 