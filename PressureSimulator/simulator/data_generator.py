"""
压力数据生成器
支持32*32传感器的多种压力数据生成模式
"""

import numpy as np
import json
import time
import math
from typing import Tuple, Dict, Any, Optional, List

class PressureDataGenerator:
    """32*32压力传感器数据生成器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据生成器
        
        Args:
            config: 配置字典，包含传感器参数和生成参数
        """
        self.config = config
        sensor_config = config.get('sensor', {})
        generation_config = config.get('generation', {})
        
        # 传感器参数
        self.sel_wires = sensor_config.get('selWires', 32)
        self.read_wires = sensor_config.get('readWires', 32)
        self.total_nodes = sensor_config.get('totalNodes', 1024)
        self.shape = (self.sel_wires, self.read_wires)
        
        # 生成参数
        self.intensity = generation_config.get('intensity', 0.5)
        self.noise_level = generation_config.get('noiseLevel', 0.1)
        self.data_range = generation_config.get('dataRange', [0, 4095])
        
        # 内部状态
        self.frame_count = 0
        self.start_time = time.time()
        
        # 加载模式配置
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> Dict[str, Any]:
        """加载压力模式配置"""
        try:
            with open('config/patterns.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("警告: patterns.json文件未找到，使用默认模式")
            return self._get_default_patterns()
    
    def _get_default_patterns(self) -> Dict[str, Any]:
        """获取默认模式配置"""
        return {
            "random": {
                "type": "random",
                "parameters": {"distribution": "exponential", "scale": 100, "intensity": 0.5}
            },
            "circle": {
                "type": "circle", 
                "parameters": {"radius": 8, "intensity": 3000, "center": [16, 16]}
            }
        }
    
    def generate_frame(self, mode: str = 'random', **kwargs) -> np.ndarray:
        """
        生成一帧32*32压力数据
        
        Args:
            mode: 生成模式 ('random', 'circle', 'line', 'wave', 'pattern')
            **kwargs: 额外参数
            
        Returns:
            32*32的压力数据数组 (uint16)
        """
        self.frame_count += 1
        current_time = time.time() - self.start_time
        
        if mode == 'random':
            data = self._generate_random()
        elif mode == 'circle':
            data = self._generate_circle(**kwargs)
        elif mode == 'line':
            data = self._generate_line(**kwargs)
        elif mode == 'wave':
            data = self._generate_wave(current_time, **kwargs)
        elif mode == 'footprint':
            data = self._generate_footprint(**kwargs)
        elif mode == 'multi_point':
            data = self._generate_multi_point(**kwargs)
        elif mode == 'pattern':
            pattern_name = kwargs.get('pattern_name', 'random')
            data = self._apply_pattern(pattern_name, **kwargs)
        else:
            print(f"未知模式: {mode}, 使用随机模式")
            data = self._generate_random()
        
        # 添加噪声
        if self.noise_level > 0:
            data = self.add_noise(data, self.noise_level)
        
        # 确保数据范围正确
        data = np.clip(data, self.data_range[0], self.data_range[1])
        
        return data.astype(np.uint16)
    
    def _generate_random(self) -> np.ndarray:
        """生成随机压力数据"""
        # 使用指数分布模拟真实的压力分布
        base_pressure = np.random.exponential(100, self.shape) * self.intensity
        
        # 添加一些空白区域（无压力）
        mask = np.random.random(self.shape) > 0.7
        base_pressure[mask] = 0
        
        return base_pressure
    
    def _generate_circle(self, center: Optional[Tuple[int, int]] = None, 
                        radius: int = 8, intensity: int = 3000, 
                        falloff: str = 'gaussian') -> np.ndarray:
        """生成圆形压力模式"""
        if center is None:
            center = (self.sel_wires // 2, self.read_wires // 2)
        
        data = np.zeros(self.shape)
        y, x = np.ogrid[:self.sel_wires, :self.read_wires]
        
        # 计算到中心的距离
        distance = np.sqrt((x - center[1])**2 + (y - center[0])**2)
        
        if falloff == 'gaussian':
            # 高斯衰减
            data = intensity * np.exp(-(distance**2) / (2 * (radius/2)**2))
        else:
            # 线性衰减
            data[distance <= radius] = intensity * (1 - distance[distance <= radius] / radius)
        
        return data
    
    def _generate_line(self, position: int = 16, width: int = 3, 
                      intensity: int = 2500, direction: str = 'horizontal') -> np.ndarray:
        """生成线性压力模式"""
        data = np.zeros(self.shape)
        
        if direction == 'horizontal':
            start_row = max(0, position - width // 2)
            end_row = min(self.sel_wires, position + width // 2 + 1)
            data[start_row:end_row, :] = intensity
        else:  # vertical
            start_col = max(0, position - width // 2)
            end_col = min(self.read_wires, position + width // 2 + 1)
            data[:, start_col:end_col] = intensity
        
        return data
    
    def _generate_wave(self, time_step: float, amplitude: int = 2000, 
                      frequency: float = 0.2, direction: str = 'horizontal',
                      speed: float = 1.0) -> np.ndarray:
        """生成波浪压力模式"""
        data = np.zeros(self.shape)
        
        if direction == 'horizontal':
            for i in range(self.sel_wires):
                for j in range(self.read_wires):
                    wave_value = amplitude * (1 + np.sin(2 * np.pi * frequency * j + speed * time_step)) / 2
                    data[i, j] = wave_value
        else:  # vertical
            for i in range(self.sel_wires):
                for j in range(self.read_wires):
                    wave_value = amplitude * (1 + np.sin(2 * np.pi * frequency * i + speed * time_step)) / 2
                    data[i, j] = wave_value
        
        return data
    
    def _generate_footprint(self, center: Optional[Tuple[int, int]] = None,
                           width: int = 12, height: int = 20, 
                           intensity: int = 4000) -> np.ndarray:
        """生成足迹压力模式（椭圆形）"""
        if center is None:
            center = (self.sel_wires // 2, self.read_wires // 2)
        
        data = np.zeros(self.shape)
        y, x = np.ogrid[:self.sel_wires, :self.read_wires]
        
        # 椭圆方程
        ellipse = ((x - center[1]) / (width / 2))**2 + ((y - center[0]) / (height / 2))**2
        mask = ellipse <= 1
        
        # 椭圆内部强度随距离中心的距离衰减
        data[mask] = intensity * (1 - ellipse[mask])
        
        return data
    
    def _generate_multi_point(self, points: Optional[List[Dict]] = None) -> np.ndarray:
        """生成多点压力模式"""
        if points is None:
            # 默认多点配置
            points = [
                {"center": [10, 10], "radius": 4, "intensity": 3000},
                {"center": [22, 22], "radius": 6, "intensity": 2500},
                {"center": [10, 22], "radius": 3, "intensity": 3500}
            ]
        
        data = np.zeros(self.shape)
        
        for point in points:
            center = point.get('center', [16, 16])
            radius = point.get('radius', 5)
            intensity = point.get('intensity', 2000)
            
            point_data = self._generate_circle(center, radius, intensity)
            data = np.maximum(data, point_data)  # 取最大值避免覆盖
        
        return data
    
    def _apply_pattern(self, pattern_name: str, **kwargs) -> np.ndarray:
        """应用预定义的压力模式"""
        if pattern_name not in self.patterns:
            print(f"模式 '{pattern_name}' 未找到，使用随机模式")
            return self._generate_random()
        
        pattern_config = self.patterns[pattern_name]
        pattern_type = pattern_config.get('type', 'random')
        params = pattern_config.get('parameters', {})
        
        # 合并kwargs参数
        params.update(kwargs)
        
        if pattern_type == 'random':
            return self._generate_random()
        elif pattern_type == 'circle':
            return self._generate_circle(**params)
        elif pattern_type == 'line':
            return self._generate_line(**params)
        elif pattern_type == 'wave':
            current_time = time.time() - self.start_time
            return self._generate_wave(current_time, **params)
        elif pattern_type == 'custom':
            return self._generate_footprint(**params)
        elif pattern_type == 'multi_point':
            return self._generate_multi_point(params.get('points'))
        else:
            return self._generate_random()
    
    def add_noise(self, data: np.ndarray, level: float = 0.1) -> np.ndarray:
        """
        添加噪声到压力数据
        
        Args:
            data: 原始压力数据
            level: 噪声水平 (0.0-1.0)
            
        Returns:
            添加噪声后的数据
        """
        noise_amplitude = np.max(data) * level
        noise = np.random.normal(0, noise_amplitude / 3, data.shape)
        return data + noise
    
    def to_1d_array(self, data_2d: np.ndarray) -> np.ndarray:
        """
        将2D压力数据转换为1D数组（用于传输）
        
        Args:
            data_2d: 32*32的2D压力数据
            
        Returns:
            1024长度的1D数组
        """
        return data_2d.flatten()
    
    def from_1d_array(self, data_1d: np.ndarray) -> np.ndarray:
        """
        将1D压力数据转换为2D数组（用于可视化）
        
        Args:
            data_1d: 1024长度的1D数组
            
        Returns:
            32*32的2D压力数据
        """
        return data_1d.reshape(self.shape)


if __name__ == "__main__":
    # 测试代码
    config = {
        'sensor': {'selWires': 32, 'readWires': 32, 'totalNodes': 1024},
        'generation': {'intensity': 0.5, 'noiseLevel': 0.1, 'dataRange': [0, 4095]}
    }
    
    generator = PressureDataGenerator(config)
    
    # 测试各种模式
    print("测试随机数据生成...")
    random_data = generator.generate_frame('random')
    print(f"随机数据形状: {random_data.shape}, 数据范围: {random_data.min()}-{random_data.max()}")
    
    print("\n测试圆形模式...")
    circle_data = generator.generate_frame('circle', radius=10, intensity=3000)
    print(f"圆形数据形状: {circle_data.shape}, 最大值: {circle_data.max()}")
    
    print("\n测试转换...")
    data_1d = generator.to_1d_array(circle_data)
    data_2d_restored = generator.from_1d_array(data_1d)
    print(f"1D数组长度: {len(data_1d)}")
    print(f"转换正确性: {np.array_equal(circle_data, data_2d_restored)}") 