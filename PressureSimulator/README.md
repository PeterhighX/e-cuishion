# 32*32 压力传感器数据模拟器

## 项目简介

本项目为 WiReSensPy 无线触觉传感系统的数据模拟器，用于生成 32*32 (1024个节点) 的压力传感器数据，验证整个可视化程序的完整性。

## 功能特性

- ✅ 支持32*32 (1024节点) 压力数据生成
- ✅ 多种压力分布模式：随机、圆形、线性、波浪、足迹、多点
- ✅ 完全兼容 WiReSensPy 数据协议格式
- ✅ WiFi TCP 数据传输
- ✅ 实时数据发送（可配置帧率）
- ✅ 动态模式切换和参数调整
- ✅ 数据包完整性验证
- ✅ 详细的日志和统计信息

## 安装和设置

### 1. 环境要求

- Python 3.7+
- numpy, scipy, matplotlib 等科学计算库

### 2. 安装依赖

```bash
cd PressureSimulator
pip install -r requirements.txt
```

### 3. 配置文件

编辑 `config/simulator_config.json` 设置：

```json
{
  "sensor": {
    "id": 1,
    "selWires": 32,
    "readWires": 32,
    "nodesPerPacket": 256
  },
  "transmission": {
    "targetIP": "10.0.0.67",
    "targetPort": 7000
  },
  "generation": {
    "frameRate": 30,
    "intensity": 0.5
  }
}
```

## 使用方法

### 1. 基础使用

```bash
cd examples
python basic_simulation.py
```

### 2. 程序化使用

```python
from simulator.data_generator import PressureDataGenerator
from sender.wifi_sender import WifiSender

# 创建配置
config = {
    'sensor': {'selWires': 32, 'readWires': 32, 'totalNodes': 1024},
    'generation': {'intensity': 0.5, 'noiseLevel': 0.1, 'dataRange': [0, 4095]}
}

# 创建数据生成器
generator = PressureDataGenerator(config)

# 生成压力数据
pressure_data = generator.generate_frame('circle', radius=10, intensity=3000)

# 创建WiFi发送器
sender = WifiSender(target_ip="10.0.0.67", target_port=7000, sensor_id=1)

# 连接并发送数据
if sender.connect():
    sender.send_frame(pressure_data)
    sender.disconnect()
```

### 3. 支持的压力模式

#### 随机模式
```python
data = generator.generate_frame('random')
```

#### 圆形模式
```python
data = generator.generate_frame('circle', 
    center=(16, 16), radius=8, intensity=3000)
```

#### 线性模式
```python
data = generator.generate_frame('line', 
    position=16, width=3, direction='horizontal', intensity=2500)
```

#### 波浪模式
```python
data = generator.generate_frame('wave', 
    amplitude=2000, frequency=0.2, direction='horizontal')
```

#### 足迹模式
```python
data = generator.generate_frame('footprint', 
    center=(16, 16), width=12, height=20, intensity=4000)
```

#### 多点模式
```python
points = [
    {"center": [10, 10], "radius": 4, "intensity": 3000},
    {"center": [22, 22], "radius": 6, "intensity": 2500}
]
data = generator.generate_frame('multi_point', points=points)
```

## 数据格式

### 数据包结构

按照 WiReSensPy 协议，每个数据包包含：

```
| 字段 | 类型 | 大小 | 描述 |
|------|------|------|------|
| sendId | int8_t | 1字节 | 传感器ID |
| startIdx | uint16_t | 2字节 | 起始索引 |
| readings[256] | uint16_t[] | 512字节 | 传感器读数 |
| packetNumber | uint32_t | 4字节 | 数据包编号 |
```

总长度：519字节

### 数据分包

- 32*32 = 1024个节点
- 每包256个节点
- 总共4个数据包/帧

## 验证集成

### 1. 启动WiReSensPy系统

```bash
cd ../WiReSensPy
python TouchSensorWireless.py
```

### 2. 修改目标IP

在 `config/simulator_config.json` 中设置正确的IP地址：

```json
{
  "transmission": {
    "targetIP": "你的WiReSensPy服务器IP",
    "targetPort": 7000
  }
}
```

### 3. 运行模拟器

```bash
cd examples
python basic_simulation.py
```

选择选项2测试连接，然后选择选项4运行模式演示。

## 故障排除

### 连接失败

1. 检查 WiReSensPy 系统是否在运行
2. 确认IP地址和端口配置正确
3. 检查防火墙设置
4. 确认网络连接正常

### 数据不显示

1. 验证数据包格式是否正确
2. 检查传感器ID配置
3. 确认数据范围 (0-4095)
4. 查看WiReSensPy日志输出

### 性能问题

1. 降低帧率设置
2. 减少包间延迟
3. 优化网络配置
4. 检查CPU和内存使用

## 开发和扩展

### 添加新的压力模式

1. 在 `simulator/data_generator.py` 中添加新的 `_generate_xxx()` 方法
2. 在 `config/patterns.json` 中添加模式配置
3. 在 `generate_frame()` 方法中添加新模式的处理

### 支持其他协议

1. 继承 `ProtocolHandler` 类
2. 实现协议特定的编码/解码逻辑
3. 创建对应的发送器类

## 项目结构

```
PressureSimulator/
├── simulator/              # 数据生成模块
│   ├── data_generator.py    # 压力数据生成器
│   ├── pattern_generator.py # 模式生成器
│   └── noise_generator.py   # 噪声生成器
├── sender/                  # 数据发送模块
│   ├── wifi_sender.py       # WiFi发送器
│   ├── serial_sender.py     # 串口发送器
│   └── protocol_handler.py  # 协议处理器
├── config/                  # 配置文件
│   ├── simulator_config.json
│   └── patterns.json
├── examples/                # 示例程序
│   ├── basic_simulation.py  # 基础示例
│   ├── pattern_demo.py      # 模式演示
│   └── stress_test.py       # 压力测试
├── tools/                   # 工具程序
│   ├── data_validator.py    # 数据验证
│   └── performance_test.py  # 性能测试
├── requirements.txt         # 依赖文件
├── README.md               # 使用说明
└── 开发文档.md             # 开发文档
```

## 许可证

本项目为开源项目，遵循MIT许可证。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进项目。

## 联系

如有问题或建议，请联系开发团队。 