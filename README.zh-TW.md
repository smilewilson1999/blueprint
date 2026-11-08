<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/cover-dark.png">
  <img src="docs/cover.png" alt="blueprint：讓團隊真的能一起審的架構圖與拆解圖。前方是 Neon 上釘著訪客留言的架構圖，後方是一個爆炸分解的晶片封裝" width="100%">
</picture>

<div align="center">

用一句話描述你在做的東西，agent 會把它畫成一個互動頁面，<br>團隊直接在 artifact.cafe 上審，不用註冊。

[![Release](https://img.shields.io/github/v/release/smilewilson1999/blueprint?color=B25F28&labelColor=2B2622)](https://github.com/smilewilson1999/blueprint/releases/latest) [![License](https://img.shields.io/github/license/smilewilson1999/blueprint?color=B25F28&labelColor=2B2622)](LICENSE) [![Agent skill](https://img.shields.io/badge/agent-skill-B25F28?labelColor=2B2622)](https://agentskills.io) [![Review on artifact.cafe](https://img.shields.io/badge/review-artifact.cafe-B25F28?labelColor=2B2622)](https://artifact.cafe)

[English](README.md) · **繁體中文** · [日本語](README.ja.md)

</div>

## 三個 skill

| Skill | 畫什麼 |
| --- | --- |
| **blueprint** | 軟體架構：服務、請求路徑、雲端基礎設施 |
| **blueprint-teardown** | 實體結構的爆炸分解圖：晶片封裝、電路板、裝置 |
| **blueprint-space** | 實體空間：辦公室、平面圖、房間與可編輯的家具配置 |

```bash
npx skills add smilewilson1999/blueprint --skill blueprint
npx skills add smilewilson1999/blueprint --skill blueprint-teardown
npx skills add smilewilson1999/blueprint --skill blueprint-space
```

支援 Claude Code、Codex、Cursor，以及[其他支援 skills 的 agent](https://agentskills.io)。在 Claude apps 裡，請從 [Releases](https://github.com/smilewilson1999/blueprint/releases/latest) 下載對應的 zip 上傳。裝好之後直接說：

> *「幫我畫我們的架構：Next.js 和 Hono API 跑在 Vercel，Postgres 用 Neon，登入用 Clerk，金流用 Stripe。」*

**直接試試看：**[結帳架構圖](https://artifact.cafe/a/acme-checkout-platform-vb1hn0) · [CoWoS 拆解圖](https://artifact.cafe/a/cowos-package-teardown-9wbulc)。不用註冊，可以縮放、點部件、留言。

## blueprint

<img src="docs/demo.webp" alt="示範：滑過元件會亮出它的連線；切到 Request path 分頁時，路徑以外的部分會變淡；點 Hono 會打開 inspector；最後切成暗色主題" width="100%">

- **一條路徑，一眼看懂。** 請求路徑用琥珀色標出並編號，圖下方附白話的步驟說明。
- **可以切換的流程。** 請求路徑、夜間同步、部署，每個分頁只亮出自己的線，其餘變淡。
- **每個元件都能點開看。** 滑過去看它跟誰相連，點下去看它的角色、說明和連結。
- **像設計軟體一樣縮放。** 滾輪往上放大、往下縮小，以游標為中心；拖曳空白處可以平移。手機上用兩指縮放。
- **不用算座標。** agent 只寫一份簡短的 [`blueprint.json`](skills/blueprint/references/spec.md)，build 負責排版、繞線，還會在你看到之前先抓出所有重疊。

## 範例

<table>
  <tr>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/ai-dark.png">
        <img src="docs/ai.png" alt="AI app: a user asks Next.js on Vercel, which runs a vector search on Supabase and sends a prompt to Claude; Inngest syncs Notion every night and writes embeddings to Supabase" width="100%">
      </picture>
      <p><b>AI 應用</b><br><sub>Next.js、Supabase pgvector、Claude，加上 Notion 夜間同步。</sub></p>
    </td>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/aws-dark.png">
        <img src="docs/aws.png" alt="AWS: CloudFront in front of S3 and an ALB in a public subnet; Fargate, RDS and ElastiCache in a private subnet of a VPC" width="100%">
      </picture>
      <p><b>AWS</b><br><sub>subnet、VPC 和服務 icon，都照 AWS 自己的畫法。</sub></p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/gcp-dark.png">
        <img src="docs/gcp.png" alt="Google Cloud: a global load balancer in front of Cloud Storage and GKE; GKE, Cloud SQL and Memorystore in one region of a VPC" width="100%">
      </picture>
      <p><b>Google Cloud</b><br><sub>region 放在 VPC 裡，全域服務放在外面。</sub></p>
    </td>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/azure-dark.png">
        <img src="docs/azure.png" alt="Azure: Front Door in front of Blob Storage and App Service in Japan East; SQL Database and Managed Redis behind private endpoints in a virtual network" width="100%">
      </picture>
      <p><b>Azure</b><br><sub>VNet 裡的 private endpoint，服務名稱照 Microsoft 要求寫全名。</sub></p>
    </td>
  </tr>
  <tr>
    <td colspan="2" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/teardown-gallery-dark.png">
        <img src="docs/teardown-gallery.png" alt="CoWoS 式封裝先顯示組合狀態，再拆成九個附標註的部件，從 BGA 錫球到銅蓋" width="100%">
      </picture>
      <p><b>晶片封裝，用 blueprint-teardown 畫</b><br><sub>CoWoS 式封裝的組合與爆炸視圖。HBM 數量和 DRAM 層數可以用滑桿調整，可下載 SVG、PNG、PDF。概念圖，尺寸為虛構。</sub></p>
    </td>
  </tr>
  <tr>
    <td colspan="2" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/space-dark.png">
        <img src="docs/space.png" alt="虛構共享辦公室 Juniper Commons 的 3D 視圖，含六個具名空間、家具、平面圖切換、配置編輯與 JSON 匯出" width="100%">
      </picture>
      <p><b>可以重新配置的空間，用 blueprint-space 畫</b><br><sub>Juniper Commons，一間虛構的共享辦公室。旋轉 3D 視角、切換平面圖、點選房間與家具，沿格線拖曳或旋轉家具，再匯出 space.json 重新建置。可離線使用。</sub></p>
    </td>
  </tr>
</table>

## 在 artifact.cafe 上審

三個 skill 產出的都是一個自給自足的 HTML 檔。agent 把它發佈到 [artifact.cafe](https://artifact.cafe)，給你一個連結。審查者點任何部件、標籤或文字就能留言，不用註冊。設計改了，agent 發佈新版本，並逐則回覆。

<img src="docs/review.png" alt="結帳架構圖上的三則訪客留言：琥珀色的釘選標記落在 Neon、webhook 標籤和 Clerk 上，旁邊的留言列表顯示每則討論和它所指的位置" width="100%">

## 更多

<details>
<summary><b>亮色與暗色</b></summary>
<br>

每張圖都有亮色和暗色兩種主題，會跟著讀者的系統設定切換。架構圖的元件底色維持淺色，讓每個 logo 保留原本的顏色。

<img src="docs/light-dark.png" alt="文件問答機器人的架構圖沿對角線切開：左上是亮色主題，右下是暗色主題" width="100%">
</details>

<details>
<summary><b>只用官方 logo，絕不重畫</b></summary>
<br>

logo 來自 [svgl](https://svgl.app)、[devicon](https://devicon.dev)、[gilbarbara/logos](https://github.com/gilbarbara/logos) 或品牌自己的 repo；[AWS](https://aws.amazon.com/architecture/icons/)、[Google Cloud](https://cloud.google.com/icons) 和 [Azure](https://learn.microsoft.com/en-us/azure/architecture/icons/) 則用各家的官方 icon 套件。佇列、排程這類抽象概念用 [Lucide](https://lucide.dev) 圖示。logo 一律不改色：放在淺色底上會看不見的，就改放深色底。
</details>

<details>
<summary><b>跑範例</b></summary>
<br>

blueprint 需要 Python 3.9 以上，並能連網下載 logo：

```bash
cd examples/saas
python3 ../../skills/blueprint/scripts/fetch_icons.py icons vercel nextjs hono neon clerk stripe github "actions:githubactions"
cp ../../skills/blueprint/assets/generic/user.svg icons/
python3 ../../skills/blueprint/scripts/blueprint.py blueprint.json icons index.html
```

blueprint-teardown 需要 Node 22 以上：

```bash
cd examples/cowos
npm install && npm run build    # dist/index.html
npm run film                    # 選用：示範影片，需要 Python Playwright 和 ffmpeg
```

blueprint-space 需要 Python 3.9 以上，可離線建置。輸出 PNG 與瀏覽器檢查另外需要 Python Playwright 和 Chromium：

```bash
cd examples/juniper-commons
python3 ../../skills/blueprint-space/scripts/space.py space.json index.html --strict
python3 ../../skills/blueprint-space/scripts/check_space.py index.html check/
python3 ../../skills/blueprint-space/scripts/render_png.py index.html space.png --view both
```

輸出 PNG 和 proof 需要 Playwright 和 Chromium。
</details>

## 致謝與授權

blueprint 從 caru-ini 的 [stack-diagram](https://github.com/caru-ini/stack-diagram) fork 而來，保留了它的 icon 抓取流程和各家雲端的繪圖規則。blueprint-teardown 的繪圖引擎來自 Jakub Krehel 的 [teardown](https://github.com/jakubkrehel/skills/tree/main/skills/teardown)，我們做的修改列在 [`engine/PATCHES.md`](skills/blueprint-teardown/engine/PATCHES.md)。

- 程式碼與文件：MIT，見 [`LICENSE`](LICENSE)。
- `skills/blueprint-teardown/engine/` 裡的 teardown 引擎：MIT，Copyright (c) 2026 Jakub Krehel，見 [`engine/LICENSE`](skills/blueprint-teardown/engine/LICENSE)。
- `skills/blueprint-space/assets/vendor/` 內附的 three.js **0.170.0**：MIT，見 [`vendor/LICENSE`](skills/blueprint-space/assets/vendor/LICENSE) 與 [`vendor/PATCHES.md`](skills/blueprint-space/assets/vendor/PATCHES.md)。
- 內附字型（Inter、IBM Plex Mono）：SIL Open Font License 1.1，見 [`assets/fonts`](skills/blueprint/assets/fonts)。
- 空間 skill 也在 [`blueprint-space/assets/fonts`](skills/blueprint-space/assets/fonts) 內附相同的 OFL 字型。
- logo **不**隨附在 repo 裡，而是在 build 時從上述來源下載。`docs/` 裡的圖片含有第三方 logo。所有品牌名稱與 logo 皆為各自擁有者的商標，出現在圖中不代表任何背書。
