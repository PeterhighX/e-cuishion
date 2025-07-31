"""
基础压力传感器模拟示例
演示如何使用32*32压力传感器模拟器发送数据到WiReSensPy系统
"""

import sys
import os
import json
import time

# 添加模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from simulator.data_generator import PressureDataGenerator
from sender.wifi_sender import WifiSender

class BasicSimulator:
    """基础压力传感器模拟器"""
    
    def __init__(self, config_file: str = None):
        """
        初始化模拟器
        
        Args:
            config_file: 配置文件路径
        """
        # 加载配置
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'simulator_config.json')
        
        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # 创建数据生成器
        self.data_generator = PressureDataGenerator(self.config)
        
        # 创建WiFi发送器
        transmission_config = self.config.get('transmission', {})
        self.wifi_sender = WifiSender(
            target_ip=transmission_config.get('targetIP', '10.0.0.67'),
            target_port=transmission_config.get('targetPort', 7000),
            sensor_id=self.config.get('sensor', {}).get('id', 1),
            nodes_per_packet=self.config.get('sensor', {}).get('nodesPerPacket', 256)
        )
        
        # 设置帧率
        generation_config = self.config.get('generation', {})
        self.wifi_sender.frame_rate = generation_config.get('frameRate', 30)
        
        print("基础模拟器初始化完成")
        print(f"目标地址: {transmission_config.get('targetIP')}:{transmission_config.get('targetPort')}")
        print(f"传感器ID: {self.config.get('sensor', {}).get('id', 1)}")
        print(f"帧率: {self.wifi_sender.frame_rate} FPS")
    
    def test_data_generation(self):
        """测试数据生成功能"""
        print("\n=== 测试数据生成 ===")
        
        # 测试随机数据
        print("生成随机压力数据...")
        random_data = self.data_generator.generate_frame('random')
        print(f"随机数据: 形状={random_data.shape}, 范围={random_data.min()}-{random_data.max()}")
        
        # 测试圆形模式
        print("生成圆形压力模式...")
        circle_data = self.data_generator.generate_frame('circle', radius=10, intensity=3000)
        print(f"圆形模式: 形状={circle_data.shape}, 最大值={circle_data.max()}")
        
        # 测试线性模式
        print("生成线性压力模式...")
        line_data = self.data_generator.generate_frame('line', width=5, intensity=2500)
        print(f"线性模式: 形状={line_data.shape}, 最大值={line_data.max()}")
        
        # 测试波浪模式
        print("生成波浪压力模式...")
        wave_data = self.data_generator.generate_frame('wave', amplitude=2000, frequency=0.1)
        print(f"波浪模式: 形状={wave_data.shape}, 最大值={wave_data.max()}")
        
        return True
    
    def test_connection(self):
        """测试连接功能"""
        print("\n=== 测试连接 ===")
        
        if self.wifi_sender.connect(timeout=5.0):
            print("连接成功！")
            
            # 发送测试数据
            test_data = self.data_generator.generate_frame('circle', radius=8, intensity=2000)
            if self.wifi_sender.send_frame(test_data):
                print("测试数据发送成功")
            else:
                print("测试数据发送失败")
            
            self.wifi_sender.disconnect()
            return True
        else:
            print("连接失败！请检查:")
            print("1. WiReSensPy系统是否在运行")
            print("2. 目标IP和端口是否正确")
            print("3. 网络连接是否正常")
            return False
    
    def run_random_simulation(self, duration: float = 30.0):
        """
        运行随机数据模拟
        
        Args:
            duration: 模拟持续时间（秒）
        """
        print(f"\n=== 运行随机数据模拟 ({duration}秒) ===")
        
        if not self.wifi_sender.connect():
            print("连接失败，无法开始模拟")
            return False
        
        def generate_random_data():
            return self.data_generator.generate_frame('random')
        
        try:
            self.wifi_sender.send_continuous(generate_random_data, duration=duration)
            return True
        except KeyboardInterrupt:
            print("用户中断模拟")
            return False
        finally:
            self.wifi_sender.disconnect()
    
    def run_pattern_demo(self, pattern_duration: float = 5.0):
        """
        运行模式演示
        
        Args:
            pattern_duration: 每个模式持续时间（秒）
        """
        print(f"\n=== 运行模式演示 (每个模式{pattern_duration}秒) ===")
        
        if not self.wifi_sender.connect():
            print("连接失败，无法开始演示")
            return False
        
        patterns = ['random', 'circle', 'line', 'wave', 'footprint', 'multi_point']
        
        try:
            for pattern in patterns:
                print(f"当前模式: {pattern}")
                
                def generate_pattern_data():
                    if pattern == 'circle':
                        return self.data_generator.generate_frame(pattern, radius=10, intensity=3000)
                    elif pattern == 'line':
                        return self.data_generator.generate_frame(pattern, width=5, intensity=2500)
                    elif pattern == 'wave':
                        return self.data_generator.generate_frame(pattern, amplitude=2000, frequency=0.2)
                    elif pattern == 'footprint':
                        return self.data_generator.generate_frame(pattern, width=15, height=25, intensity=3500)
                    elif pattern == 'multi_point':
                        return self.data_generator.generate_frame(pattern)
                    else:
                        return self.data_generator.generate_frame('random')
                
                self.wifi_sender.send_continuous(generate_pattern_data, duration=pattern_duration)
                print(f"模式 {pattern} 完成")
            
            return True
            
        except KeyboardInterrupt:
            print("用户中断演示")
            return False
        finally:
            self.wifi_sender.disconnect()
    
    def run_dynamic_simulation(self, duration: float = 60.0):
        """
        运行动态模拟（模式自动切换）
        
        Args:
            duration: 总持续时间（秒）
        """
        print(f"\n=== 运行动态模拟 ({duration}秒) ===")
        
        if not self.wifi_sender.connect():
            print("连接失败，无法开始模拟")
            return False
        
        patterns = ['circle', 'line', 'wave', 'random']
        pattern_switch_interval = 10.0  # 每10秒切换模式
        
        start_time = time.time()
        
        def generate_dynamic_data():
            elapsed = time.time() - start_time
            current_pattern_index = int(elapsed / pattern_switch_interval) % len(patterns)
            current_pattern = patterns[current_pattern_index]
            
            if current_pattern == 'circle':
                # 动态圆形：半径随时间变化
                radius = 5 + int(5 * abs(np.sin(elapsed * 0.5)))
                return self.data_generator.generate_frame('circle', radius=radius, intensity=3000)
            elif current_pattern == 'line':
                # 动态线条：位置随时间移动
                position = int(16 + 10 * np.sin(elapsed * 0.3))
                return self.data_generator.generate_frame('line', position=position, width=3, intensity=2500)
            elif current_pattern == 'wave':
                return self.data_generator.generate_frame('wave', amplitude=2000, frequency=0.2)
            else:
                return self.data_generator.generate_frame('random')
        
        try:
            # 需要导入numpy
            import numpy as np
            
            self.wifi_sender.send_continuous(generate_dynamic_data, duration=duration)
            return True
            
        except KeyboardInterrupt:
            print("用户中断模拟")
            return False
        except ImportError:
            print("需要numpy库支持动态模拟")
            return False
        finally:
            self.wifi_sender.disconnect()


def main():
    """主函数"""
    print("32*32压力传感器模拟器 - 基础示例")
    print("=" * 50)
    
    try:
        # 创建模拟器
        simulator = BasicSimulator()
        
        while True:
            print("\n请选择操作:")
            print("1. 测试数据生成")
            print("2. 测试连接")
            print("3. 运行随机数据模拟 (30秒)")
            print("4. 运行模式演示")
            print("5. 运行动态模拟 (60秒)")
            print("0. 退出")
            
            choice = input("请输入选择 (0-5): ").strip()
            
            if choice == '1':
                simulator.test_data_generation()
            elif choice == '2':
                simulator.test_connection()
            elif choice == '3':
                simulator.run_random_simulation(30.0)
            elif choice == '4':
                simulator.run_pattern_demo(5.0)
            elif choice == '5':
                simulator.run_dynamic_simulation(60.0)
            elif choice == '0':
                break
            else:
                print("无效选择，请重试")
        
        print("感谢使用模拟器！")
        
    except FileNotFoundError as e:
        print(f"配置文件未找到: {e}")
        print("请确保config/simulator_config.json文件存在")
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        print(f"程序运行时发生错误: {e}")


if __name__ == "__main__":
    main() 