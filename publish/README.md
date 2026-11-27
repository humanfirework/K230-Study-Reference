# release/ —— 发布说明

这个目录只服务于 GitHub Release，不参与板子上的代码。

| 文件 | 作用 |
| --- | --- |
| `RELEASE_NOTES.md` | Release 正文（中文），由 workflow 读取 |
| `build_assets.py` | 在 CI 里生成索引、真题 zip、2025 工程 zip，并复制打印清单 |
| `../.github/workflows/release.yml` | push `v*` tag 时自动建/更新 Release 并上传四个附件 |

## 发版

```bash
git tag -a v2026.11 -m "2026-11 documentation overhaul"
git push origin v2026.11
```

推送 tag 后，Actions 会自动跑 `Build release assets` → `Publish`。也可以到 Actions 页面手动 Run workflow，输入一个已存在的 tag。

⚠️ 附件是每次现生成的，**正文不是**：发新版前先改 `RELEASE_NOTES.md` 的标题和内容（尤其是“这一版做了什么”和版本号），否则新 release 会沿用上一版的说明。

## 附件从哪来

- `nuedc_papers_1994-2026.zip`、`nuedc_paper_index.md`：每次从 `NUEDC_TOPIC-master/真题/` 现生成，不把 42 MB 的包塞进 git。
- `2025_E_self_aiming.zip`：从 `07_contest/2025_E_self_aiming/` 现打包，排除 `__pycache__`。
- `checklist_A4.pdf`：**预生成**的 A4 打印版，源是 `docs/05_competition_checklist.md`。改了清单要重新生成 `docs/assets/checklist_A4.pdf` 再提交。

## 为什么不用手动上传

Release 的写入需要 `contents: write`。workflow 里的 `GITHUB_TOKEN` 由 GitHub 按次签发，不需要个人 PAT；前提是仓库的 Actions 权限允许写（Settings → Actions → General → Workflow permissions 选 “Read and write permissions”）。
