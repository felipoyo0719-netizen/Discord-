# Division 2 エスカレーション目標アイテム → Discord 自動通知

Discord の指定チャンネルに、**エスカレーション目標アイテムのデータが変わった場合だけ**投稿する仕組みです。15分間隔でチェックします。ショップ全体や DC/NY の目標アイテム全域の監視は、この版には含まれません。

## 初期設定（PCの常時起動は不要）

1. Discord の投稿先チャンネルの **チャンネルを編集 → 連携サービス → ウェブフック** からウェブフックを作り、URLをコピーする（「ウェブフックの管理」権限が必要）。
2. GitHub にログインし、新しいリポジトリを作る。自分だけで管理したい場合は Private にしてもOK（無料枠の Actions 使用量は確認してください）。
3. このZIPを展開し、**`.github/workflows/check.yml` を含むフォルダー構成を保ったまま**新しいリポジトリへアップロードしてコミットする。ブラウザの Add file → Upload files や GitHub Desktop が使えます。
4. GitHubリポジトリの **Settings → Secrets and variables → Actions → New repository secret** で、名前を `DISCORD_WEBHOOK_URL`、値にコピーしたウェブフックURLを入れる。
5. **Settings → Actions → General → Workflow permissions** が Read and write permissions であることを確認（リポジトリ/組織の設定によっては変更が必要）。
6. **Actions → Division 2 loot change watcher → Run workflow** で初回テスト。初回は現在のデータを1件投稿します。その後は変化したときだけ投稿されます。

## 仕組み

- 元データ: https://hi-dep.github.io/division2/data/event/index.json
- 表示リンク: https://hidep-division2.pages.dev/?lang=ja&view=target_loot
- 日本時間の当日またはそれ以前で最も新しい `Escalation` の `target_loot_by_day` を取得。
- `state/last_snapshot.json` に前回通知したデータを記録し、変更がない場合は何も投稿しません。
- 投稿成功時のみ状態を更新し、そのJSONをGitHubに自動コミットします。

## 注意点

- 即時通知ではありません。15分おきの確認とGitHub Actions側の起動遅延があります。
- GitHub Actionsのスケジュールは混雑状況で遅延・スキップする場合があります。
- 公開リポジトリで60日間活動がないと、GitHubが定期ワークフローを停止することがあります。
- リンク先のデータ構造が変わった場合は修正が必要です。
- ウェブフックURLは第三者に見せないこと。コードやスクリーンショットに貼り付けないでください。
- 自動投稿はサイト運営者がデータ更新した後になります。ゲーム内更新からの時間は一定ではありません。
- プロトタイプキャッシュの表示はソースデータの値をそのまま使うため、日本語名でない場合があります。
