# 無料PDFツールの「アップロード不要」検証：生データ

記事「[無料PDFツールは本当に『アップロード不要』なのか、通信ログで確認した](https://aishigoto-lab.com/review/pdf-tool-upload-network-check/)」で使った、検証データの全部です。

## 検証日時・環境

- 検証日：2026年9月6日（日本時間）
- ブラウザ：Chromium系ブラウザ（Claude内蔵ブラウザ、Chromium 148系）
- OS：Windows（ユーザー環境のリモートブラウザ経由）

## 対象にした4つ

| # | ツール | 機能 | 種別 |
|---|---|---|---|
| 1 | [FreeTool](https://freetool.jp/pdf/compress) | PDF圧縮 | 「アップロード不要」を明示 |
| 2 | [pdfux](https://pdfux.com/ja/assaku-pdf/) | PDF圧縮 | 「アップロード不要」を明示 |
| 3 | [ポケットツールズ（ep-melody）](https://www.ep-melody.com/tools/pdfcomb/) | PDF結合 | 「サーバーに送信されず端末上で処理」を明示 |
| 4 | [iLovePDF](https://www.ilovepdf.com/ja/compress_pdf) | PDF圧縮 | 対照群。アップロード不要を謳っていない、通常のクラウド処理サービス |

4番目のiLovePDFは「アップロード不要」を主張していない、素直にサーバーへアップロードして処理するサービスです。
**今回の計測手法が実際のアップロードを正しく検出できるか**を確認するための対照実験として加えました。

## ダミーPDFの作り方

`make_dummy_pdf.py` で作った、意味のないテキストだけのPDFです。実在の文書は一切使っていません。

- ファイルサイズ：2895バイト（固定・再現可能）
- 圧縮をかけずに生成しているため、ファイルの生バイト列に `AISHIGOTO-LAB-TEST-8823-NETLOG` という目印文字列がそのまま残っている
- `dummy_test.pdf` と `dummy_test2.pdf` は同一内容（結合テストで2ファイル必要なツール用）

## 測り方

1. 各ツールのページを開き、ページ内のJavaScriptで `window.fetch` と `XMLHttpRequest.prototype.send` を差し替える（後述のコード）。以降、ページが行うすべての通信のURL・メソッド・送信内容（FormDataの中身まで）を記録する
2. `<input type="file">` に対して、`DataTransfer` 経由でダミーPDFの `File` オブジェクトを設定し `change` イベントを発火させる（実際にファイル選択ダイアログでファイルを選ぶのと、ページ側のJavaScriptからは区別がつかない）
3. 各ツールの実行ボタン（圧縮する／結合する）を押す
4. 記録された通信の一覧を確認し、ファイル名・ファイルサイズ・ファイル内容のマーカー文字列が含まれる通信がないかを確認する
5. 念のため、ブラウザのネットワーク要求一覧（開発者ツールのNetworkタブに相当する機能）と `performance.getEntriesByType('resource')` でも二重に確認する

### 通信を記録するコード（実際に使ったもの）

```javascript
window.__netlog = [];
function log(entry){ window.__netlog.push(entry); }
function describeBody(body){
  if (!body) return {bodySize:0};
  if (body instanceof FormData) {
    const parts = [];
    for (const [k,v] of body.entries()) {
      if (v instanceof File) parts.push({key:k, isFile:true, name:v.name, size:v.size, type:v.type});
      else parts.push({key:k, isFile:false, value: String(v).slice(0,200)});
    }
    return {isFormData:true, parts};
  }
  if (typeof body === 'string') return {bodySize: body.length, textPreview: body.slice(0,300)};
  if (body.size) return {bodySize: body.size};
  return {bodySize: -1};
}
const origFetch = window.fetch;
window.fetch = function(input, init){
  const url = (typeof input === 'string') ? input : input.url;
  const desc = describeBody(init && init.body);
  log(Object.assign({type:'fetch', url, method: (init&&init.method)||'GET', time: Date.now()}, desc));
  return origFetch.apply(this, arguments);
};
const origOpen = XMLHttpRequest.prototype.open;
const origSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function(method, url){
  this.__logMethod = method; this.__logUrl = url;
  return origOpen.apply(this, arguments);
};
XMLHttpRequest.prototype.send = function(body){
  const desc = describeBody(body);
  log(Object.assign({type:'xhr', url: this.__logUrl, method: this.__logMethod, time: Date.now()}, desc));
  return origSend.apply(this, arguments);
};
```

## ファイル一覧

| ファイル | 内容 |
|---|---|
| `make_dummy_pdf.py` | 検証用ダミーPDFの生成スクリプト |
| `dummy_test.pdf` / `dummy_test2.pdf` | 実際にアップロードしたダミーPDF（2895バイト） |
| `netlog_1_freetool.json` | FreeToolでの検証記録 |
| `netlog_2_pdfux.json` | pdfuxでの検証記録 |
| `netlog_3_epmelody.json` | ポケットツールズでの検証記録 |
| `netlog_4_ilovepdf_control.json` | iLovePDF（対照群）での検証記録 |
| `summary.csv` | 4件の結果一覧（表計算ソフトで開けます） |

## この検証で言えないこと（限界）

- **ファイル選択の方法**：実際にファイル選択ダイアログを操作したのではなく、JavaScriptの `DataTransfer` を使ってFileオブジェクトを注入した。ページ側のJavaScriptからは通常の選択と区別がつかないが、「本物のクリック（isTrusted）」を厳密に要求する特殊な実装のツールでは通用しない可能性がある（今回の4件はすべて問題なく処理された）
- **検出できるのはfetch/XMLHttpRequest経由の通信のみ**：`navigator.sendBeacon` など別の送信手段を使っていた場合は、今回のコードでは記録されない（4件とも、それらしき挙動は見当たらなかった）
- **観測範囲は「ファイルを追加してから処理完了まで」**：ページ読み込み時や、処理完了後にユーザーがさらに操作した場合の通信は対象外
- **各ツール1回のみの実行**：設定を変えたり、画像を多く含むPDF・大きいPDFを使った場合の挙動は未確認
- **検証したのは圧縮・結合機能のみ**：OCRやパスワード解除など、原理的にサーバー側の処理が必要な機能は対象外
- **ダミーPDFは機密情報を含まないテキストのみ**：実在の機密文書での挙動そのものを観察したわけではない
- **検証時点（2026年9月6日）の実装が対象**：各サービスの実装は将来変わりうる

## 誤りを見つけた場合

[お問い合わせ](https://aishigoto-lab.com/contact/)からご指摘ください。確認のうえ訂正し、いつ・どこを・なぜ訂正したかを記事に明記します。
