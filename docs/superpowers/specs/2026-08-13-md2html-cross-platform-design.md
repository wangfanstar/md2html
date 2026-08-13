# md2html.py 通用化设计(Windows / Linux)

日期:2026-08-13
状态:已获用户批准(方案 A:单文件增强)

## 目标

将 `md2html.py` 从「仅支持 README.md → README.html、标题日期硬编码、仅 Linux 文档」的单点工具,适配为可在 Windows 和 Linux 上通用的 Markdown → HTML 转换工具,并同步更新 `md2html工具说明.md`。

## 背景与现状问题

当前 `md2html.py`(约 748 行,单文件):

1. 只接受一个工作目录参数,固定读取 `README.md`、输出 `README.html`
2. HTML 标题("Autogen — GT SDK Code Generation Engineer's Guide")、侧边栏标题、副标题、页脚("v2.0 · Auto-generated from README.md · 2026-08")全部硬编码
3. 文档 `md2html工具说明.md` 中路径写的是 `scripts/md2html.py`,与实际位置不符;用法只有 `python3`,未覆盖 Windows
4. 无 argparse,无 `--title` 等选项

代码本身已使用 `pathlib` 与显式 `utf-8` 读写,路径处理天然跨平台,不需要重写。

## 需求

### R1:多模式 argparse CLI

```
用法:
  python md2html.py                      # 无参数 → 当前目录 README.md → README.html
  python md2html.py <dir>                # 目录 → <dir>/README.md → <dir>/README.html(兼容旧用法)
  python md2html.py <input.md>           # 文件 → 同目录同名 .html
  python md2html.py <input.md> -o out.html   # 显式指定输出
  python md2html.py --title "标题" <input.md>  # 手动指定标题
```

- 参数:`--title TEXT`(手动指定标题)、`-o/--output PATH`(输出文件)
- 无参数且当前目录无 README.md 时:报错并 exit 1
- 输入文件不存在时:报错并 exit 1
- 输出目录不存在时:自动创建
- 路径解析统一使用 `Path.resolve()`

### R2:标题与日期动态化

- 标题来源优先级:`--title` 参数 > 文档第一个 `# h1` 的文本 > 输入文件名(stem)
- 标题用于 HTML `<title>` 和侧边栏 header
- 侧边栏副标题:显示输入文件名(如 `README.md`),替代硬编码 "GT SDK Code Generator"
- 页脚:显示源文件名 + 动态日期(格式 `YYYY-MM`,`datetime.now()` 生成),去掉硬编码 "2026-08" 与 "v2.0" 字样
- 正文中 `## 目录` TOC 段落的移除逻辑保持不变

### R3:平台兼容处理

- 启动时对 `sys.stdout`/`sys.stderr` 执行 `reconfigure(encoding='utf-8')`(Windows 默认 GBK 控制台下打印中文不乱码),用 try/except 包裹以兼容 stdout 被重定向或非 TextIOWrapper 的环境;项目要求 Python 3.8+,无需低版本回退
- 输出文件:UTF-8 无 BOM、`\n` 换行(保持现状)
- 文档写明命令差异:Windows 用 `python`,Linux 用 `python3`;由启动脚本自动探测

### R4:启动脚本

- `md2html.bat`(Windows):依次探测 `py -3`、`python`、`python3`,用第一个可用的解释器调用 `md2html.py` 并传递所有参数(`%*`)
- `md2html.sh`(Linux/macOS):依次探测 `python3`、`python`,同理传递所有参数(`"$@"`),脚本需可执行权限(chmod +x)
- 脚本与 `md2html.py` 同目录,按脚本自身路径定位 `md2html.py`(不依赖调用时的工作目录)

### R5:文档更新

更新 `md2html工具说明.md`:

- 修正路径引用为实际文件位置
- 新增完整 CLI 用法与参数表
- 新增 Windows/Linux 双平台用法示例(含启动脚本说明)
- 更新「处理流程」「自定义」章节,匹配新代码结构(标题/日期动态化)
- 依赖章节注明:`pygments` 在较新版本 `markdown` 中为可选(codehilite 内置 lexers 可用),保持现有安装说明不变

## 非目标(YAGNI)

- 不拆分 CSS/JS 模板为独立文件(方案 B,保持单文件拷贝即用)
- 不增加批量转换、watch 模式、配置文件
- 不改动现有 HTML 的 CSS/JS 交互逻辑(侧边栏高亮、移动端折叠等)
- 不引入第三方 CLI 依赖(argparse 为标准库)

## 代码结构变更

保持单文件,变更点:

1. `__main__` 块重写:argparse 定义参数 → 解析输入/输出路径 → 调 `convert()`
2. `convert()` 签名改为 `convert(input_path, output_path, title=None)`,内部:
   - 读取 markdown 后提取第一个 h1(正则 `^#\s+(.+)$`)
   - 计算标题、副标题、日期
   - HTML 模板中三处硬编码(标题、侧边栏 header、页脚)替换为 f-string 变量
3. 新增 `main(argv)` 函数便于测试;`if __name__ == '__main__'` 调用 `sys.exit(main())`
4. 新增 `md2html.bat`、`md2html.sh`

## 错误处理

| 场景 | 行为 |
|------|------|
| 输入文件不存在 | stderr 报错,exit 1 |
| 无参数且当前目录无 README.md | stderr 提示用法,exit 1 |
| 输出路径为目录 | stderr 报错,exit 1 |
| 输入文件非 UTF-8 | 保持现状(`errors` 默认 strict,Python 抛异常) |

## 测试与验证

环境:Windows 11(本机,Python 3.x)为主验证平台;Linux 语法层面通过 `python -m py_compile` 验证(无 Linux 实机时说明)。

手工验证清单:

1. 无参数运行(目录内有 README.md)→ 生成 README.html,标题为文档第一个 h1
2. `md2html.py 输入.md` → 同目录生成同名 .html
3. `md2html.py 输入.md -o 输出目录/new.html` → 自动建目录并生成
4. `--title "自定义"` → HTML `<title>` 与侧边栏标题均为自定义值
5. 输入不存在的文件 → exit 1 + 报错
6. `md2html.bat 输入.md`(cmd 下)→ 结果与直接 python 调用一致
7. 生成 HTML 浏览器打开:侧边栏 TOC、章节编号、滚动高亮、代码高亮、明暗主题正常
8. 无 h1 的 md 文件 → 标题回退为文件名
9. `md2html.sh` 语法检查(`bash -n`)

## 影响范围

- `md2html.py`:修改(约 +60/-30 行,主要在主函数与模板注入处)
- `md2html.bat`、`md2html.sh`:新增
- `md2html工具说明.md`:重写部分章节
- 无其他文件受影响;旧用法(目录模式、README.md → README.html)完全兼容
