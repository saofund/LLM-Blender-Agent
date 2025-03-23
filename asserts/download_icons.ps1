$iconsDir = "asserts/icons"; mkdir -Force $iconsDir; $icons = @{"claude" = "https://claude.ai/favicon.ico"; "zhipu" = "https://chatglm.cn/favicon.ico"; "deepseek" = "https://www.deepseek.com/favicon.ico"; "doubao" = "https://lf-flow-web-cdn.doubao.com/obj/flow-doubao/samantha/logo-icon-white-bg.png"; "moonshot" = "https://www.moonshot.cn/favicon.ico"; "aimlapi" = "https://aiml.com/favicon.ico"}; foreach ($model in $icons.Keys) {$url = $icons[$model]; $output = "$iconsDir/$model.png"; Write-Host "正在下载 $model 图标: $url"; try {Invoke-WebRequest -Uri $url -OutFile $output; Write-Host "成功下载到: $output"} catch {Write-Host "下载失败: $_"}}; Write-Host "图标下载完成！"
