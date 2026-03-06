# Jama Project Data Export Script

このスクリプトは、Jamaのプロジェクトの内容をJSONファイルに保存するためのツールです。

## 概要

`SaveJamaItems.py` は、Jama Connect からプロジェクト情報、アイテム、リレーション、ピックリスト等のデータを取得し、JSONファイルとして保存します。

## 出力先

実行したディレクトリ配下の `json` フォルダにファイルが作成されます。
- `project_itemtypes.json` - アイテムタイプ一覧
- `pick_lists.json` - ピックリスト一覧
- `pick_list_{id}_options.json` - 各ピックリストのオプション
- `relationshiptypes.json` - リレーションタイプ一覧
- `project_{id}.json` - プロジェクト情報
- `project_{id}_items.json` - プロジェクトのアイテム一覧
- `project_{id}_relations.json` - プロジェクトのリレーション一覧

## 環境変数の設定

実行前に以下の環境変数を設定してください。

### BASIC認証の場合:
```
set AUTH_TYPE=BASIC
set JAMA_URL=https://your-jama-instance.com
set JAMA_USERNAME=your_username
set JAMA_PASSWORD=your_password
```

### OAUTH認証の場合:
```
set AUTH_TYPE=OAUTH
set JAMA_URL=https://your-jama-instance.com
set JAMA_CLIENT_ID=XXX
set JAMA_CLIENT_SECRET=XXX
```

## 実行方法

環境変数を設定した後、以下のコマンドで実行してください：

```
python SaveJamaItems.py
```


## 注意事項

- BASIC認証を使用する場合、SSL証明書の検証が無効になります
- スクリプト実行時に `json` フォルダが自動的に作成されます
- 大きなプロジェクトの場合、実行に時間がかかる場合があります