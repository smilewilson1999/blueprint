<div align="center">

# blueprint

**チームでちゃんとレビューできるアーキテクチャ図。**

技術スタックを一文で伝えるだけ。エージェントが公式ロゴと一本の明快なリクエスト経路で図を描き、<br>レビュアーがそのままコメントできるインタラクティブなページに仕上げます。

[![License](https://img.shields.io/github/license/smilewilson1999/blueprint?color=B25F28&labelColor=2B2622)](LICENSE) [![Agent skill](https://img.shields.io/badge/agent-skill-B25F28?labelColor=2B2622)](https://agentskills.io) [![Review on artifact.cafe](https://img.shields.io/badge/review-artifact.cafe-B25F28?labelColor=2B2622)](https://artifact.cafe)

[English](README.md) · [繁體中文](README.zh-TW.md) · **日本語**

</div>

<br>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/hero-dark.png">
  <img src="docs/hero.png" alt="アーキテクチャ図：ユーザーが HTTPS で Vercel 上の Next.js にアクセスし、Next.js が RPC で Hono API を呼び出す。Hono は SQL で Neon を参照し、Clerk でセッションを確認し、Stripe で決済を開始する。Stripe は webhook で応答する。GitHub Actions がデプロイする" width="100%">
</picture>

<p align="center"><sub><i>「うちのスタックを図にして。Next.js と Hono の API を Vercel で、Postgres は Neon、認証は Clerk、決済は Stripe。デプロイは GitHub Actions。」</i></sub></p>

## インストール

```bash
npx skills add smilewilson1999/blueprint
```

Claude Code、Codex、Cursor など、[skills に対応したエージェント](https://agentskills.io)で使えます。あとは図を頼むだけです。

## 画像ではなく、ページです

<img src="docs/demo.gif" alt="デモ：コンポーネントにカーソルを合わせると接続先が光り、Request path タブで経路以外が薄くなり、Hono をクリックするとインスペクタが開き、テーマがダークに切り替わる" width="100%">

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>たどるべき経路は一本</h3>
      リクエスト経路はアンバーで番号付き。図の下には平易な言葉のステップ一覧が並び、ほかの要素は一歩下がります。
    </td>
    <td width="50%" valign="top">
      <h3>フローを切り替えられる</h3>
      リクエスト経路、夜間同期、デプロイ。フローごとにタブがあり、選ぶとその線だけが光ってほかは薄くなります。
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>すべての部品にインスペクタ</h3>
      カーソルを合わせると接続先がわかり、クリックすると役割、採用の理由、リポジトリやダッシュボードへのリンクが表示されます。
    </td>
    <td width="50%" valign="top">
      <h3>コメントされる前提で設計</h3>
      名前、役割、線のラベルはすべて実テキストで、固定の id を持ちます。フィードバックは対象のコンポーネントに留まり、版を重ねても外れません。
    </td>
  </tr>
</table>

## 仕組み

**1. エージェントがシステムを記述する。** 座標もピクセル計算も不要です。ノードはグリッドに置き、グループはメンバーを列挙し、線は両端を指定するだけ。

```json
{
  "groups": [{ "id": "vercel", "label": "Vercel", "icon": "vercel", "contains": ["next", "hono"] }],
  "nodes": [
    { "id": "next", "name": "Next.js", "role": "frontend", "icon": "nextjs", "at": [1, 0] },
    { "id": "hono", "name": "Hono", "role": "api routes", "icon": "hono", "at": [2, 0] }
  ],
  "edges": [{ "from": "next", "to": "hono", "label": "RPC", "kind": "primary", "step": 2 }]
}
```

**2. 描画はビルドに任せる。** メンバーからグループの大きさを決め、ノードやラベルを避けて線を引き、双方向の線にはそれぞれのレーンを割り当てます。重なりを見つけるとすべて報告するので、あなたが見る前にエージェントが直します。

**3. artifact.cafe でレビューする。** できあがるのは自己完結した HTML ファイル一つ。エージェントが [artifact.cafe](https://artifact.cafe) に公開してリンクを渡します。レビュアーはアカウントなしでコメントでき、構成が変われば新しい版が公開され、以前のコメントは対象の部品に付いたまま残ります。

静止画が必要なときは、ライトとダークの PNG も書き出せます。Slack、スライド、README にどうぞ。

## ギャラリー

<table>
  <tr>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/ai-dark.png">
        <img src="docs/ai.png" alt="AI アプリ：ユーザーが Vercel 上の Next.js に質問し、Next.js が Supabase でベクトル検索して Claude にプロンプトを送る。Inngest が毎晩 Notion を同期し、埋め込みを Supabase に書き込む" width="100%">
      </picture>
      <p><b>AI アプリ</b><br><sub>ドキュメント Q&amp;A ボット：Next.js、Supabase pgvector、Claude、Inngest による Notion の夜間同期。</sub></p>
    </td>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/aws-dark.png">
        <img src="docs/aws.png" alt="AWS：CloudFront が S3 と public subnet の ALB の前段にあり、Fargate、RDS、ElastiCache は VPC の private subnet にある" width="100%">
      </picture>
      <p><b>AWS は AWS 公式アイコンで</b><br><sub>サブネット、VPC、サービスアイコンを AWS 自身の描き方で。</sub></p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/gcp-dark.png">
        <img src="docs/gcp.png" alt="Google Cloud：グローバルロードバランサが Cloud Storage と GKE の前段にあり、GKE、Cloud SQL、Memorystore は VPC 内の一つのリージョンにある" width="100%">
      </picture>
      <p><b>Google Cloud は Google 公式アイコンで</b><br><sub>リージョンは VPC の中に、グローバルなサービスはその外に。</sub></p>
    </td>
    <td width="50%" valign="top">
      <picture>
        <source media="(prefers-color-scheme: dark)" srcset="docs/azure-dark.png">
        <img src="docs/azure.png" alt="Azure：Front Door が Blob Storage と Japan East の App Service の前段にあり、SQL Database と Managed Redis は仮想ネットワーク内の private endpoint 経由で接続される" width="100%">
      </picture>
      <p><b>Azure は Microsoft 公式アイコンで</b><br><sub>VNet 内の private endpoint。サービス名は Microsoft の求めるとおり正式名称で。</sub></p>
    </td>
  </tr>
</table>

## 公式ロゴだけ、描き直さない

ロゴは [svgl](https://svgl.app)、[devicon](https://devicon.dev)、[gilbarbara/logos](https://github.com/gilbarbara/logos)、またはブランド自身のリポジトリから取得し、[AWS](https://aws.amazon.com/architecture/icons/)、[Google Cloud](https://cloud.google.com/icons)、[Azure](https://learn.microsoft.com/en-us/azure/architecture/icons/) は各社公式のアイコンパッケージを使います。キューや cron のような概念には [Lucide](https://lucide.dev) のピクトグラムを。ロゴの色は決して変えません。明るいタイルで見えなくなるなら、暗いタイルに載せます。

## サンプルを動かす

```bash
cd examples/saas
python3 ../../skills/blueprint/scripts/fetch_icons.py icons vercel nextjs hono neon clerk stripe github "actions:githubactions"
cp ../../skills/blueprint/assets/generic/user.svg icons/
python3 ../../skills/blueprint/scripts/blueprint.py blueprint.json icons index.html
open index.html
```

Python 3.9 以上と、ロゴ取得のためのネットワーク接続が必要です。PNG の書き出しには Playwright と Chromium を使います。spec の形式は [`references/spec.md`](skills/blueprint/references/spec.md) にあります。

## クレジットとライセンス

blueprint は caru-ini による [stack-diagram](https://github.com/caru-ini/stack-diagram) のフォークとして始まり、そのアイコン取得の仕組みとクラウドベンダーごとの描画ルールを引き継いでいます。

- コードとドキュメント：MIT。[`LICENSE`](LICENSE) を参照。
- 同梱フォント（Inter、IBM Plex Mono）：SIL Open Font License 1.1。[`assets/fonts`](skills/blueprint/assets/fonts) を参照。
- ロゴは同梱して**いません**。ビルド時に上記の提供元からダウンロードします。`docs/` の画像には第三者のロゴが含まれます。ブランド名とロゴはすべて各所有者の商標であり、図での使用は推奨や提携を意味しません。
