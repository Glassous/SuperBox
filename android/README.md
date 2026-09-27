# Superbox Android

使用 Jetpack Compose 和 Material 3 的原生客户端。首页搜索、JSON、Base64、URL、时间戳及 EXIF 工具均调用现有 FastAPI，不在设备上复制后端运算。

工具目录只在应用进程冷启动时请求一次，之后首页搜索仅筛选内存中的目录。云端未提供的本地功能显示为禁用；云端新增但当前版本没有页面的功能仍显示卡片，并提示更新应用。目录加载失败时本次进程不重试，完全退出并重新启动应用后才会再次请求。新增本地功能时，建立独立 Screen（自带 Scaffold 与顶部栏，接收 `onBack` 处理返回），并在 `LocalToolRegistry` 登记 slug、路由和备用文案；导航与目录匹配会自动纳入该功能。导航层只保留纯 `NavHost`，不提供共享顶部栏，每个功能页都是完整页面，切换时整页使用 NavHost 默认过渡动画。应用使用边到边显示（`enableEdgeToEdge`），状态栏与底部小白条都保持透明并沉浸：页面 Scaffold 的 `contentWindowInsets` 置零，顶部内边距由各页 `TopAppBar` 自理，底部安全距离由可滚动内容的内边距加 `WindowInsets.navigationBars` 保证，因此新页面不要改用默认的 Scaffold 内边距。

## API 地址

`android/.env` 已配置：

```dotenv
SUPERBOX_API_BASE_URL=https://superbox.fiacloud.top/
```

Gradle 在构建时读取这个地址，系统或 CI 中同名环境变量优先。地址填写服务根路径，不包含 `/api/v1`；末尾斜杠会自动移除。`.env` 被 Git 忽略，提交配置示例时使用 `.env.example`。更改地址后重新构建 App。

Debug 构建在两处均未配置时使用 `http://10.0.2.2:8087`，适用于 Android 模拟器访问开发机后端。真机调试时，将环境变量设为真机可访问的局域网地址并重新构建。Release 构建必须提供 HTTPS 地址。API 文档按钮会在浏览器打开该地址的 `/docs`。

## 构建与验证

使用 Android Studio 打开 `android/`，安装 Android SDK 37 并运行 `app`。或在此目录运行：

```powershell
.\gradlew.bat :app:assembleDebug :app:testDebugUnitTest
.\gradlew.bat :app:assembleRelease
```

EXIF 选图与保存使用系统文件选择器，无需存储权限。支持 JPEG、PNG、WebP，文件不得超过 20 MB。后端需安装 ExifTool 才能处理 EXIF。
