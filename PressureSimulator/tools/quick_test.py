"""
快速测试脚本
验证32*32压力传感器模拟器的核心功能
"""

import sys
import os
import json
import traceback

# 添加模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_config_loading():
    """测试配置文件加载"""
    print("1. 测试配置文件加载...")
    try:
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'simulator_config.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"   ✅ 主配置文件加载成功")
        print(f"   - 传感器ID: {config.get('sensor', {}).get('id')}")
        print(f"   - 传感器规格: {config.get('sensor', {}).get('selWires')}×{config.get('sensor', {}).get('readWires')}")
        print(f"   - 目标地址: {config.get('transmission', {}).get('targetIP')}:{config.get('transmission', {}).get('targetPort')}")
        
        patterns_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'patterns.json')
        with open(patterns_path, 'r', encoding='utf-8') as f:
            patterns = json.load(f)
        
        print(f"   ✅ 模式配置文件加载成功")
        print(f"   - 支持模式: {list(patterns.keys())}")
        
        return True, config
    except Exception as e:
        print(f"   ❌ 配置文件加载失败: {e}")
        return False, None

def test_data_generator(config):
    """测试数据生成器"""
    print("\n2. 测试数据生成器...")
    try:
        from simulator.data_generator import PressureDataGenerator
        
        generator = PressureDataGenerator(config)
        print(f"   ✅ 数据生成器初始化成功")
        
        # 测试各种模式
        test_modes = ['random', 'circle', 'line', 'wave', 'footprint', 'multi_point']
        
        for mode in test_modes:
            try:
                data = generator.generate_frame(mode)
                if data.shape == (32, 32) and data.dtype == 'uint16':
                    print(f"   ✅ {mode}模式: 形状={data.shape}, 范围={data.min()}-{data.max()}")
                else:
                    print(f"   ❌ {mode}模式: 数据格式错误")
                    return False
            except Exception as e:
                print(f"   ❌ {mode}模式生成失败: {e}")
                return False
        
        # 测试数据转换
        test_data = generator.generate_frame('circle')
        data_1d = generator.to_1d_array(test_data)
        data_2d_restored = generator.from_1d_array(data_1d)
        
        if len(data_1d) == 1024 and test_data.shape == data_2d_restored.shape:
            print(f"   ✅ 数据转换测试通过")
        else:
            print(f"   ❌ 数据转换测试失败")
            return False
        
        return True
    except Exception as e:
        print(f"   ❌ 数据生成器测试失败: {e}")
        traceback.print_exc()
        return False

def test_protocol_handler():
    """测试协议处理器"""
    print("\n3. 测试协议处理器...")
    try:
        from sender.protocol_handler import ProtocolHandler
        import numpy as np
        
        handler = ProtocolHandler(256)
        print(f"   ✅ 协议处理器初始化成功")
        
        # 测试数据包编码/解码
        test_readings = list(range(256))
        packet_bytes = handler.encode_packet(1, 0, test_readings, 0)
        
        expected_size = 1 + (1+256)*2 + 4  # 按照协议格式计算
        if len(packet_bytes) == expected_size:
            print(f"   ✅ 数据包编码: 大小={len(packet_bytes)}字节 (期望={expected_size})")
        else:
            print(f"   ❌ 数据包编码: 大小错误 {len(packet_bytes)}!={expected_size}")
            return False
        
        # 测试解码
        decoded_id, decoded_start, decoded_readings, decoded_packet = handler.decode_packet(packet_bytes)
        if (decoded_id == 1 and decoded_start == 0 and 
            decoded_readings == test_readings and decoded_packet == 0):
            print(f"   ✅ 数据包解码: 数据匹配")
        else:
            print(f"   ❌ 数据包解码: 数据不匹配")
            return False
        
        # 测试完整性验证
        if handler.verify_packet_integrity(packet_bytes):
            print(f"   ✅ 数据包完整性验证通过")
        else:
            print(f"   ❌ 数据包完整性验证失败")
            return False
        
        # 测试1024节点分包
        test_pressure = np.random.randint(0, 4096, 1024, dtype=np.uint16)
        packets = handler.split_pressure_data(test_pressure, sensor_id=1)
        
        if len(packets) == 4:  # 1024÷256 = 4包
            print(f"   ✅ 数据分包: {len(packets)}个包")
            
            # 验证所有包
            all_valid = all(handler.verify_packet_integrity(packet_bytes) for packet_bytes, _ in packets)
            if all_valid:
                print(f"   ✅ 所有分包都有效")
            else:
                print(f"   ❌ 部分分包无效")
                return False
        else:
            print(f"   ❌ 数据分包错误: {len(packets)}包 (期望4包)")
            return False
        
        return True
    except Exception as e:
        print(f"   ❌ 协议处理器测试失败: {e}")
        traceback.print_exc()
        return False

def test_wifi_sender_creation():
    """测试WiFi发送器创建（不实际连接）"""
    print("\n4. 测试WiFi发送器创建...")
    try:
        from sender.wifi_sender import WifiSender
        
        sender = WifiSender(target_ip="127.0.0.1", target_port=7000, sensor_id=1)
        print(f"   ✅ WiFi发送器创建成功")
        print(f"   - 目标: {sender.target_ip}:{sender.target_port}")
        print(f"   - 传感器ID: {sender.sensor_id}")
        print(f"   - 帧率: {sender.frame_rate}")
        
        # 测试状态获取
        status = sender.get_status()
        print(f"   ✅ 状态获取成功: 连接={status['connected']}")
        
        return True
    except Exception as e:
        print(f"   ❌ WiFi发送器测试失败: {e}")
        traceback.print_exc()
        return False

def test_integration():
    """测试整体集成"""
    print("\n5. 测试整体集成...")
    try:
        from simulator.data_generator import PressureDataGenerator
        from sender.wifi_sender import WifiSender
        
        # 创建配置
        config = {
            'sensor': {'selWires': 32, 'readWires': 32, 'totalNodes': 1024},
            'generation': {'intensity': 0.5, 'noiseLevel': 0.1, 'dataRange': [0, 4095]}
        }
        
        # 创建组件
        generator = PressureDataGenerator(config)
        sender = WifiSender(target_ip="127.0.0.1", target_port=7000, sensor_id=1)
        
        # 生成数据
        pressure_data = generator.generate_frame('circle', radius=10, intensity=3000)
        print(f"   ✅ 数据生成: 形状={pressure_data.shape}")
        
        # 模拟发送流程（不实际连接）
        pressure_1d = generator.to_1d_array(pressure_data)
        tcp_packets = sender.protocol_handler.prepare_tcp_data(sender.sensor_id, pressure_1d)
        print(f"   ✅ 数据分包: {len(tcp_packets)}个TCP包")
        
        # 验证数据包
        total_bytes = sum(len(packet) for packet in tcp_packets)
        expected_bytes = 4 * (1 + (1+256)*2 + 4)  # 4包 × 包大小
        if total_bytes == expected_bytes:
            print(f"   ✅ 总数据大小: {total_bytes}字节 (期望={expected_bytes})")
        else:
            print(f"   ❌ 总数据大小错误: {total_bytes}!={expected_bytes}")
            return False
        
        print(f"   ✅ 整体集成测试通过")
        return True
        
    except Exception as e:
        print(f"   ❌ 整体集成测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("32*32压力传感器模拟器 - 快速测试")
    print("=" * 50)
    
    tests = [
        test_config_loading,
        lambda: test_data_generator(config) if config else False,
        test_protocol_handler,
        test_wifi_sender_creation,
        test_integration
    ]
    
    config = None
    passed = 0
    total = len(tests)
    
    for i, test in enumerate(tests):
        try:
            if i == 0:  # 配置加载测试
                success, config = test()
            else:
                success = test()
            
            if success:
                passed += 1
            else:
                break  # 如果有测试失败，停止后续测试
                
        except Exception as e:
            print(f"   ❌ 测试执行异常: {e}")
            break
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！模拟器核心功能正常")
        print("\n接下来可以:")
        print("1. 运行 examples/basic_simulation.py 进行完整测试")
        print("2. 启动WiReSensPy系统并测试数据传输")
        print("3. 根据需要调整配置参数")
    else:
        print("❌ 部分测试失败，请检查安装和配置")
        print("\n排除故障:")
        print("1. 检查依赖包是否安装完整: pip install -r requirements.txt")
        print("2. 检查配置文件是否正确")
        print("3. 查看详细错误信息")

if __name__ == "__main__":
    main() 