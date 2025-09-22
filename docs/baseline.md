### Baseline and Standards

本项目在 Windows 迷你主机（本机 MQTT）上运行，所有服务以独立进程方式启动，并通过 MQTT 进行解耦通信。统一采用 JSON Lines 日志格式（UTC 时间）。

#### 目录结构（MVP）
- `config/`: 配置文件（端口、日志、清单、MQTT）
- `docs/`: 文档（基线、主题、部署、FAQ 等）
- `releases/current/orchestrator/`: 编排器（进程管理、意图路由、健康检查）
- `releases/current/overlay/`: 叠加层（TopMost 透明窗口）
- `releases/current/voice/`: 语音（VAD/唤醒词/ASR/规则NLU/TTS）
- `releases/current/sdk-unity/`: Unity 侧 SDK 示例
- `releases/current/sample-game/`: 示例游戏（或替代进程）
- `tests/`: 冒烟与 E2E 测试
- `tools/`: 脚本（安装、启动、显示设置等）

#### 时间与日志
- 时间格式：UTC ISO8601（带 `Z`，如 `2025-01-01T12:34:56.789Z`）
- 日志格式：JSON Lines；统一字段：`ts`、`level`、`service`、`msg`、`context`（可选）
- 日志轮转：按文件大小（默认 1MB）与备份数（默认 3）

#### MQTT
- 本地 Broker：Mosquitto（默认 `127.0.0.1:1883`）
- 主题前缀：`robot/`
- 主要主题：
  - `robot/intent`：意图输入（语音、测试、UI）
  - `robot/state`：系统/游戏状态
  - `robot/overlay`：叠加层显示/交互
  - `robot/overlay/confirm`：叠加层确认回传
  - `robot/sensor/#`：传感器（可选）
  - `robot/telemetry/#`：遥测/内部指标（可选）

#### 端口与约定
- MQTT：`1883`
- 游戏健康检查：默认使用本地 HTTP 端口（示例 20080+，每个游戏可在清单中覆盖）
- 不使用硬编码绝对路径；通过相对路径或环境变量展开（如 `${WINDIR}`）。

#### 配置文件（MVP）
- `config/ports.yaml`：端口、主题前缀、日志轮转默认值
- `config/logging.json`：Python logging `dictConfig` 模板（JSON 格式化）
- `config/manifest.schema.json`：游戏清单 JSON Schema
- `config/manifest.json`：示例清单（至少一个条目，含同义词）
- `config/mosquitto.conf`：Mosquitto 本地安全配置（仅回环）

#### DoD（Definition of Done）
- 配置可缺省但有合理默认；不得依赖绝对路径
- 各服务输出 UTC JSON 日志；有一键启动/停止脚本
- MQTT 冒烟测试通过；编排器可接收意图并发布状态

