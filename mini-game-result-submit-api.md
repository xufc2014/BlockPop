# 小游戏结果上报接口文档

## 1. 接口说明

该接口用于小游戏客户端在一局游戏结束后，将本局结果上报到平台。平台会保存本次上报数据，并根据上报分数匹配奖励档位。

当前接口只负责接收上报、记录数据、判断当日是否已领取奖励、匹配奖励档位。奖励发放动作由平台后续流程处理。

## 2. 请求地址

```http
POST /api/Game/SubmitMinGameResult
Content-Type: application/json
```

说明：

- 路由大小写不敏感，推荐按上方路径调用。
- 业务处理成功或失败均返回 HTTP 200，具体结果以响应体 `code` 判断。

## 3. 请求参数

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `appid` | `int` | 是 | 小游戏应用 ID，由平台分配，用于区分不同小游戏配置、签名密钥和奖励规则 |
| `game_id` | `int` | 是 | 数据来源的平台游戏 ID，用于标识本次上报来自哪个平台游戏 |
| `nAccountID` | `int` | 是 | 玩家账号 ID |
| `role_id` | `long` | 是 | 玩家角色 ID |
| `nWorldID` | `int` | 是 | 角色所在区服/世界 ID |
| `result` | `string` | 是 | 小游戏结果原始 JSON 字符串。平台只按字符串原文保存，不解析、不重排格式 |
| `score` | `int` | 是 | 小游戏分数，用于匹配奖励档位，必须大于等于 0 |
| `timestamp` | `long` | 是 | Unix 秒级时间戳 |
| `sign` | `string` | 是 | 请求签名，32 位 MD5 字符串 |

## 4. 签名规则

签名原文按以下顺序直接拼接，不添加分隔符：

```text
appid + game_id + nAccountID + role_id + nWorldID + result + score + timestamp + SECRET_KEY
```

签名计算：

```text
sign = MD5(签名原文)
```

接入要求：

- `SECRET_KEY` 由平台分配，请勿写入客户端可轻易提取的位置。
- `result` 必须使用请求中实际提交的字符串原文参与签名。
- `result` 不要在签名前后重新格式化，例如不要改变字段顺序、空格、换行或转义形式。
- `timestamp` 与服务器时间相差不能超过 300 秒。
- 服务端校验签名时忽略大小写，建议客户端统一传 32 位小写 MD5。

## 5. 请求示例

### 5.1 JSON 请求体

```json
{
  "appid": 1,
  "game_id": 2160,
  "nAccountID": 10001,
  "role_id": 20002,
  "nWorldID": 101,
  "result": "{\"level_reached\":5,\"stars\":4,\"duration\":120}",
  "score": 5500,
  "timestamp": 1781078400,
  "sign": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
}
```

### 5.2 签名示例

假设：

```text
appid      = 1
game_id    = 2160
nAccountID = 10001
role_id    = 20002
nWorldID   = 101
result     = {"level_reached":5,"stars":4,"duration":120}
score      = 5500
timestamp  = 1781078400
SECRET_KEY = abc123
```

签名原文为：

```text
121601000120002101{"level_reached":5,"stars":4,"duration":120}55001781078400abc123
```

最终：

```text
sign = MD5("121601000120002101{\"level_reached\":5,\"stars\":4,\"duration\":120}55001781078400abc123")
```

注意：示例中的 `SECRET_KEY` 和 `sign` 仅用于说明，正式接入以平台分配值为准。

## 6. 响应格式

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | `int` | 处理结果。`1` 表示成功，`0` 表示失败 |
| `msg` | `string` | 处理结果说明 |

## 7. 响应示例

### 7.1 成功

```json
{
  "code": 1,
  "msg": "奖励已匹配，等待发放"
}
```

### 7.2 今日已领取

```json
{
  "code": 0,
  "msg": "今日奖励已领取"
}
```

### 7.3 校验失败

```json
{
  "code": 0,
  "msg": "校验失败，请通过游戏内启动"
}
```

常见原因：

- 必填参数缺失或非法。
- `appid` 或 `game_id` 未配置。
- `sign` 签名错误。
- `timestamp` 超过 5 分钟有效期。

### 7.4 数据异常

```json
{
  "code": 0,
  "msg": "数据异常，请联系GM"
}
```

常见原因：

- `score` 未命中奖励档位。
- 平台奖励规则配置异常。
- 平台内部处理异常。

## 8. 接入注意事项

1. 每次上报都必须使用当前请求的实际 `result` 字符串参与签名。
2. `result` 是原始结果扩展字段，平台不会解析该 JSON；奖励匹配只使用顶层 `score`。
3. `score` 必须放在请求体顶层，不要只放在 `result` 内部。
4. 同一角色同一自然日内，已经成功领取过奖励后，再次上报会返回“今日奖励已领取”。
5. 客户端收到 `code=0` 时，应直接展示或按业务策略处理 `msg`，不要重复高频重试。
6. 请确保客户端与服务器时间同步，避免 `timestamp` 校验失败。

## 9. 联调检查清单

- 已从平台获取 `appid`、`game_id` 和 `SECRET_KEY`。
- 请求体字段名与本文档完全一致，包括 `nAccountID`、`nWorldID` 的大小写。
- `result` 签名前后的字符串内容完全一致。
- `score` 为顶层整数参数。
- `timestamp` 为 Unix 秒级时间戳，不是毫秒级时间戳。
- `sign` 按指定字段顺序拼接后计算 MD5。
