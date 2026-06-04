# Nuitka 打包操作说明

## 环境说明

- 项目目录：`I:\plane_game`
- 源码目录：`I:\plane_game\game_project`
- 虚拟环境：`I:\plane_game\games`
- 输出目录：`I:\plane_game\game_project\dist`

---

## 打包步骤

### 第一步：打开 CMD

按 `Win + R`，输入 `cmd`，回车打开命令提示符。

---

### 第二步：进入项目目录

```
cd /d I:\plane_game
```

---

### 第三步：激活虚拟环境

```
games\Scripts\activate
```

激活成功后，命令行前面会出现 `(games)` 字样，例如：

```
(games) I:\plane_game>
```

---

### 第四步：进入源码目录

```
cd game_project
```

---

### 第五步：执行打包命令

#### 打包 game.py → plane_game.exe（动物连连看，img图片库）

```
python -m nuitka --onefile --windows-console-mode=disable --enable-plugin=tk-inter --windows-icon-from-ico=img/ggico.ico --include-data-dir=img=img --output-filename=plane_game.exe --output-dir=dist --assume-yes-for-downloads game.py
```

#### 打包 game2.py → plane_game2.exe（连连看2，ggimg图片库，80张随机）

```
python -m nuitka --onefile --windows-console-mode=disable --enable-plugin=tk-inter --windows-icon-from-ico=ggimg/ggico.ico --include-data-dir=ggimg=ggimg --output-filename=plane_game2.exe --output-dir=dist --assume-yes-for-downloads game2.py
```

> 说明：首次编译耗时较长（5~15分钟），后续再打包会有缓存，速度明显加快。

---

### 第六步：确认输出

打包完成后，exe 文件在：

```
I:\plane_game\game_project\dist\plane_game.exe
I:\plane_game\game_project\dist\plane_game2.exe
```

---

## 参数说明

| 参数 | 说明 |
|---|---|
| `--onefile` | 打包成单个 exe 文件 |
| `--windows-console-mode=disable` | 运行时不弹出黑色控制台窗口 |
| `--windows-icon-from-ico=xxx.ico` | 设置 exe 文件图标 |
| `--include-data-dir=img=img` | 将 img 文件夹打包进 exe（格式：本地路径=exe内路径） |
| `--output-filename=xxx.exe` | 指定输出的 exe 文件名 |
| `--output-dir=dist` | 指定输出目录 |
| `--assume-yes-for-downloads` | 自动同意下载所需工具，无需手动确认 |

---

## 注意事项

1. **图标文件**：`ggico.ico` 必须放在对应图片目录内（`img/` 或 `ggimg/`）
2. **图片目录**：`--include-data-dir` 要和代码里 `resource_path("img/...")` 的路径保持一致
3. **每次修改源码后**都需要重新执行第五步的打包命令
4. **build 目录**：打包时会在 `dist` 下生成 `game.build`、`game.dist` 等临时文件夹，可以忽略，不影响使用

---

## 常见问题

**Q：打包时提示找不到编译器？**
A：确保 Visual Studio 或 Visual Studio Build Tools 已安装，Nuitka 依赖 MSVC 编译器（cl.exe）。

**Q：打包成功但运行时图片加载失败？**
A：检查 `--include-data-dir` 参数是否正确，等号左边是本地文件夹名，等号右边是 exe 内的路径名，两者必须一致。

**Q：如何验证打包结果不可反编译？**
A：Nuitka 将 Python 代码编译为 C 再生成机器码，没有 `.pyc` 字节码存在，`pyinstxtractor` 等工具无法提取源码。
