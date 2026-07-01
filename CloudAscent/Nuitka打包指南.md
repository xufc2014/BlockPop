# CloudAscent Nuitka 打包指南

## 环境要求

- Python 3.12（使用 `I:\plane_game\games\Scripts\python.exe`）
- 已安装 nuitka、pygame、requests 等依赖

## 打包步骤

### 1. 打开终端

`Win+R` → 输入 `cmd` → 回车

### 2. 进入项目目录

```cmd
cd /d I:\plane_game\game_project\CloudAscent
```

### 3. 清理旧编译产物（如果存在）

```cmd
rmdir /s /q dist
```

### 4. 执行打包

一行命令：

```cmd
I:\plane_game\games\Scripts\python.exe -m nuitka --onefile --windows-console-mode=disable --include-data-dir=img=img --include-data-dir=Sound=Sound --output-filename=CloudAscent.exe --output-dir=dist --assume-yes-for-downloads CloudAscent.py
```

### 5. 等待完成

编译约 5-15 分钟，看到 `Nuitka: Finished.` 即成功。

### 6. 输出位置

```
I:\plane_game\game_project\CloudAscent\dist\CloudAscent.exe
```

---

## 参数说明

| 参数 | 含义 |
|------|------|
| `--onefile` | 打包为单个 exe 文件 |
| `--windows-console-mode=disable` | 不显示控制台黑窗口 |
| `--include-data-dir=img=img` | 将 img 目录内所有资源打入 exe |
| `--include-data-dir=Sound=Sound` | 将 Sound 目录内所有音效打入 exe |
| `--output-filename=CloudAscent.exe` | 输出文件名 |
| `--output-dir=dist` | 输出到 dist 目录 |
| `--assume-yes-for-downloads` | 自动确认下载 C 编译器 |

---

## 启动方式

游戏大厅（plane_game.exe）通过以下参数启动：

```cmd
CloudAscent.exe --nAccountID=xxx --role_id=xxx --nWorldID=xxx --role_name=xxx --level=xxx --vip_lv=xxx
```

**不能双击直接启动**，否则会因为缺少 `role_id` 参数而弹出"启动失败"提示并退出。
