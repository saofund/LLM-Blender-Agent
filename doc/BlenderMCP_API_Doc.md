# Blender MCP 插件文档

## 1. 概述

Blender MCP (Model Control Protocol) 是一个用于连接 Blender 与 Claude AI 的插件，允许 Claude 通过 Socket 通信直接控制 Blender 进行 3D 建模和场景操作。该插件提供了一组 API 接口，支持基础场景操作、资源管理以及与第三方资源平台的集成。

## 2. 核心功能

Blender MCP 插件提供以下主要功能：
1. 基础场景操作（创建、修改、删除对象）
2. 材质和纹理管理
3. 与 Poly Haven 资源库的集成
4. 与 Hyper3D Rodin AI 模型生成服务的集成

## 3. 接入方式

### 3.1 安装与配置

1. 在 Blender 中安装 addon.py 插件
2. 在 3D 视图的侧边栏中找到 BlenderMCP 面板（按 N 键打开侧边栏）
3. 设置端口号（默认为 9876）
4. 可选：启用 Poly Haven 资源集成
5. 可选：启用 Hyper3D Rodin 3D 模型生成集成，设置 API 密钥
6. 点击"Start MCP Server"开始服务

### 3.2 通信协议

插件通过 Socket 通信，使用 JSON 格式传递命令和接收响应：

1. **请求格式**:
```json
{
  "type": "命令类型",
  "params": {
    // 命令参数...
  }
}
```

2. **响应格式**:
```json
{
  "status": "success|error",
  "result": {
    // 返回数据...
  },
  "message": "错误信息(仅在错误时)"
}
```

## 4. API 接口详细说明

### 4.1 基础场景操作接口

#### 获取场景信息
- **命令**: `get_scene_info`
- **参数**: 无
- **描述**: 获取当前场景信息，包括场景名称、对象数量等基本信息
- **示例**:
```json
{
  "type": "get_scene_info",
  "params": {}
}
```

#### 创建对象
- **命令**: `create_object`
- **参数**:
  - type: 对象类型（"CUBE", "SPHERE", "CYLINDER", "PLANE", "CONE", "TORUS", "EMPTY", "CAMERA", "LIGHT"）
  - name: 对象名称（可选）
  - location: 位置坐标 [x, y, z]（可选，默认 [0, 0, 0]）
  - rotation: 旋转角度 [x, y, z]（可选，默认 [0, 0, 0]）
  - scale: 缩放比例 [x, y, z]（可选，默认 [1, 1, 1]）
  - 其他特定参数（根据对象类型，如环面的段数等）
- **描述**: 在场景中创建指定类型的新对象

#### 修改对象
- **命令**: `modify_object`
- **参数**:
  - name: 对象名称（必需）
  - location: 新位置（可选）
  - rotation: 新旋转（可选）
  - scale: 新缩放（可选）
  - visible: 可见性（可选）
- **描述**: 修改场景中现有对象的属性

#### 删除对象
- **命令**: `delete_object`
- **参数**:
  - name: 要删除的对象名称
- **描述**: 从场景中删除指定对象

#### 获取对象信息
- **命令**: `get_object_info`
- **参数**:
  - name: 对象名称
- **描述**: 获取指定对象的详细信息，包括位置、旋转、缩放、材质等

#### 执行代码
- **命令**: `execute_code`
- **参数**:
  - code: 要执行的 Python 代码
- **描述**: 在 Blender 环境中执行任意 Python 代码（高级功能，谨慎使用）

### 4.2 材质管理接口

#### 设置材质
- **命令**: `set_material`
- **参数**:
  - object_name: 要应用材质的对象名称
  - material_name: 材质名称（可选，如果未提供将创建一个默认名称）
  - create_if_missing: 如果材质不存在是否创建（可选，默认 true）
  - color: RGBA 颜色值 [r, g, b, a]（可选）
- **描述**: 为指定对象创建或应用材质

### 4.3 Poly Haven 集成接口

#### 检查 Poly Haven 状态
- **命令**: `get_polyhaven_status`
- **参数**: 无
- **描述**: 检查 Poly Haven 集成是否已启用

#### 获取 Poly Haven 资源分类
- **命令**: `get_polyhaven_categories`
- **参数**:
  - asset_type: 资源类型（"hdris", "textures", "models", "all"）
- **描述**: 获取指定资源类型的分类列表

#### 搜索 Poly Haven 资源
- **命令**: `search_polyhaven_assets`
- **参数**:
  - asset_type: 资源类型（可选）
  - categories: 分类（可选）
- **描述**: 搜索 Poly Haven 资源库

#### 下载 Poly Haven 资源
- **命令**: `download_polyhaven_asset`
- **参数**:
  - asset_id: 资源 ID
  - asset_type: 资源类型（"hdris", "textures", "models"）
  - resolution: 分辨率（可选，默认 "1k"）
  - file_format: 文件格式（可选，根据资源类型有不同默认值）
- **描述**: 下载并导入指定的 Poly Haven 资源

#### 应用纹理
- **命令**: `set_texture`
- **参数**:
  - object_name: 要应用纹理的对象名称
  - texture_id: 已下载纹理的 ID
- **描述**: 将已下载的 Poly Haven 纹理应用到指定对象

### 4.4 Hyper3D Rodin 集成接口

#### 检查 Hyper3D 状态
- **命令**: `get_hyper3d_status`
- **参数**: 无
- **描述**: 检查 Hyper3D Rodin 集成是否已启用

#### 创建 Rodin 模型生成任务
- **命令**: `create_rodin_job`
- **参数**:
  - text_prompt: 描述要生成模型的文本提示（可选）
  - images: 参考图像列表（可选）
  - bbox_condition: 边界框条件（可选）
- **描述**: 创建 Hyper3D Rodin 模型生成任务

#### 查询任务状态
- **命令**: `poll_rodin_job_status`
- **参数**:
  - 对于 MAIN_SITE 模式: subscription_key
  - 对于 FAL_AI 模式: request_id
- **描述**: 获取当前 Rodin 任务的状态

#### 导入生成的资源
- **命令**: `import_generated_asset`
- **参数**:
  - 对于 MAIN_SITE 模式: task_uuid, name
  - 对于 FAL_AI 模式: request_id, name
- **描述**: 从 Hyper3D Rodin 导入生成的 3D 模型

## 5. 使用示例

### 创建基本立方体
```json
{
  "type": "create_object",
  "params": {
    "type": "CUBE",
    "name": "MyCube",
    "location": [0, 0, 1],
    "scale": [2, 2, 2]
  }
}
```

### 设置材质颜色
```json
{
  "type": "set_material",
  "params": {
    "object_name": "MyCube",
    "material_name": "RedMaterial",
    "color": [1, 0, 0, 1]
  }
}
```

### 使用 Poly Haven 导入纹理
```json
{
  "type": "download_polyhaven_asset",
  "params": {
    "asset_id": "rock_ground_02",
    "asset_type": "textures",
    "resolution": "2k"
  }
}
```

### 使用 Hyper3D Rodin 生成模型
```json
{
  "type": "create_rodin_job",
  "params": {
    "text_prompt": "一个精致的雕花椅子"
  }
}
```

## 6. 注意事项

1. 插件使用 Socket 通信，请确保选择的端口未被其他程序占用
2. 使用 Poly Haven 和 Hyper3D Rodin 功能需要先在界面中启用对应选项
3. Hyper3D Rodin 需要有效的 API 密钥，可以使用内置的试用密钥
4. 所有返回的数据都是 JSON 格式，处理时需要注意解析

## 7. 故障排除

1. 如果无法连接服务器，检查端口设置和防火墙配置
2. 如果 Poly Haven 资源无法下载，检查网络连接和 API 响应
3. 如果 Hyper3D Rodin 功能无法使用，验证 API 密钥是否有效
4. 命令执行错误会在响应中包含详细的错误信息 