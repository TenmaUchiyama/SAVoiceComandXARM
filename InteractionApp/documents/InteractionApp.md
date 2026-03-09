# InteractionApp 仕様書

> **目的**: CLI ツール (`pc_debug_ws_cli.py`) およびロボット操作スクリプト群を、ブラウザ上のタブ型 GUI に統合する。  
> **技術スタック**: SvelteKit 2 + Vite 7 + TypeScript (フロントのみ SPA)  
> **通信先**:
> | 接続先 | プロトコル | エンドポイント | 用途 |
> |--------|-----------|---------------|------|
> | SystemServer (FastAPI) | WebSocket | `ws://<host>:8080/spatial` | 空間推論パイプライン全般 |
> | SystemServer (FastAPI) | WebSocket | `ws://<host>:8080/status` | サーバ/ロボ状態の監視 |
> | SystemServer (FastAPI) | HTTP POST | `/command_cord`, `/command` | レガシー単発推論 |
> | SystemServer (FastAPI) | HTTP POST | `/save_grid_config` | グリッド保存 |
> | Unity/HoloLens (PCDebug WS) | WebSocket | `ws://<host>:<port>/` | キャリブレーション・ファイル同期 |

---

## 1. 全体構成

```
┌─────────────────────────────────────────────────────────┐
│                    InteractionApp (Browser)              │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐  │
│  │ Unity Tab│ │ XArm Tab │ │Spatial Tab│ │ Log Tab   │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────┘  │
│        │            │            │             │        │
│        ▼            ▼            ▼             ▼        │
│  ┌─────────────────────────────────────────────────┐    │
│  │        WebSocket / HTTP 通信レイヤ              │    │
│  │  (wsUnity: PCDebug WS | wsSpatial: /spatial   │    │
│  │   wsStatus: /status   | http: REST calls)     │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
         │                     │
    Unity/HoloLens        SystemServer (FastAPI)
                              │
                           xArm SDK
```

---

## 2. タブ構成と機能一覧

### 2.1 Unity タブ

CLI の `pc_debug_ws_cli.py` が担っていた Unity デバッグ機能をそのまま GUI 化する。

| セクション                       | UIコンポーネント                                             | 対応 CLI コマンド                            | 送信イベント / 動作                                              |
| -------------------------------- | ------------------------------------------------------------ | -------------------------------------------- | ---------------------------------------------------------------- |
| **接続状態**                     | ステータスバッジ (Connected / Disconnected)                  | `wait`                                       | — (WebSocket `onopen`/`onclose` で自動更新)                      |
| **キャリブレーション**           | ボタン群 (Teach / Restore / Record / Robot / Clear / Status) | `calib <action>`                             | `pc_debug_calibration_request { action }`                        |
| **キー入力**                     | 仮想キーパッド (W / R / Space など)                          | `key <k>`                                    | legacy `KeyInput { key }`                                        |
| **グリッド管理ローカル**         | ファイルリスト + Restore ボタン                              | `grids`, `restore [file]`                    | legacy `RestoreGridConfig { gridPoints }`                        |
| **ロボットマーカー管理ローカル** | ファイルリスト + Restore ボタン                              | `robots`, `restore_robot [file]`             | legacy `RestoreRobotMarkerConfig { markerData }`                 |
| **一括リストア**                 | 「Restore All」ボタン (Grid + Robot 同時)                    | `restore_all`                                | 上記 2 つを連続送信                                              |
| **Unityファイル閲覧**            | ツリービュー + JSON プレビュー                               | `list [recursive]`, `read <path>`            | `pc_debug_persistent_list_request`, `pc_debug_read_json_request` |
| **Unityインポート**              | Import Grid / Import Robot / Import Pair ボタン              | `import_grid`, `import_robot`, `import_pair` | READ → ローカル保存フロー                                        |
| **Raw / Legacy 送信**            | テキストエリア + 送信ボタン                                  | `raw`, `legacy`                              | 任意イベント送信                                                 |

#### 受信イベントの処理

| Unity → App イベント | GUI 上の表現                                     |
| -------------------- | ------------------------------------------------ |
| `SaveGridConfig`     | ローカル保存 → ファイルリスト更新 + トースト通知 |
| `SaveRobotConfig`    | ローカル保存 → ファイルリスト更新 + トースト通知 |
| その他（応答）       | Log タブにストリーム表示                         |

---

### 2.2 XArm タブ

SystemServer 経由でロボットを直接制御する。

| セクション               | UIコンポーネント                           | 動作                                                 |
| ------------------------ | ------------------------------------------ | ---------------------------------------------------- |
| **接続ステータス**       | バッジ (Enabled / Disabled) + IP 表示      | `/status` WebSocket で `robot_enabled` を監視        |
| **基本操作**             | ボタン群: Home / Initial Pos / Reset       | HTTP or WS 経由で XArmOperator の各メソッド呼び出し  |
| **グリッパー**           | Open / Close ボタン + 現在位置スライダー   | `open_gripper()` / `close_gripper()`                 |
| **グリッドピック**       | X, Y 数値入力 + Pick ボタン                | `pick_at(x, y)` → SystemServer 経由                  |
| **グリッドマップビュー** | 格子状の可視化 (grid_pose_map.json)        | ローカル JSON 読み込み → セルクリックで pick_at      |
| **手動ジョグ (将来)**    | 方向キー (±X ±Y ±Z) + ステップ量スライダー | keyboard_move.py 相当の REST/WS API (要 Server 拡張) |

> **注**: 手動ジョグはサーバ側に `/jog` エンドポイントを追加する必要があるため v2 スコープとする。

---

### 2.3 Spatial タブ

Spatial Reference Pipeline の対話フローを GUI 上で再現・テストする。

| セクション               | UIコンポーネント                                                         | 対応メッセージ type                         |
| ------------------------ | ------------------------------------------------------------------------ | ------------------------------------------- |
| **発話入力**             | テキスト入力 + 送信ボタン                                                | `spatial_reference_request`                 |
| **結果表示**             | カード: `top_candidate_id`, `confidence`, 候補リスト (score + reasoning) | `spatial_reference_result` (受信)           |
| **確認フィードバック**   | Accept / Reject ボタン + 自由テキスト入力                                | `confirmation_interpretation_request`       |
| **リファイン**           | テキスト入力 + 送信ボタン                                                | `refinement_request`                        |
| **ロボットコマンド状態** | ステータスバー (waiting → executing → done)                              | `robot_command` (受信)                      |
| **エラー表示**           | アラートバナー                                                           | `error`, `server_error` (受信)              |
| **オブジェクト一覧**     | テーブル: id, label, color, position                                     | リクエスト JSON の `objects[]` をプレビュー |

#### 想定フロー (GUI上)

```
[テキスト入力] → 送信 → Processing 表示
     ↓
[結果カード表示] ← spatial_reference_result
     ↓ ユーザ確認
[Accept] → confirmation_interpretation_request { "はい" }
[Reject / 言い直し] → テキスト入力 → confirmation_interpretation_request { 自由テキスト }
     ↓
[robot_command status 表示] ← robot_command
     ↓ done
[Idle に戻る]
```

---

### 2.4 Log タブ

全 WebSocket メッセージのリアルタイムモニタ。

| 機能               | 説明                                                                      |
| ------------------ | ------------------------------------------------------------------------- |
| **ストリーム表示** | TX (→ 送信) / RX (← 受信) をタイムスタンプ付きで表示。JSON は折り畳み可。 |
| **フィルタ**       | イベント名・方向 (TX/RX)・接続先 (Unity/Spatial/Status) でフィルタ        |
| **クリア**         | ログクリアボタン                                                          |
| **エクスポート**   | JSON Lines でダウンロード                                                 |

---

## 3. 通信レイヤ設計

### 3.1 WebSocket マネージャ (`$lib/ws.ts`)

```typescript
interface WsManagerOptions {
  url: string;
  autoReconnect?: boolean; // default: true
  reconnectIntervalMs?: number; // default: 3000
}

// Svelte 5 の $state で状態管理
class WsManager {
  connected: boolean; // $state
  lastError: string; // $state

  send(event: string, payload: object): void;
  sendLegacy(eventId: string, payload: object): void;
  on(event: string, handler: (data: any) => void): void;
  off(event: string): void;
  close(): void;
}
```

| インスタンス | 接続先                           | 用途                                |
| ------------ | -------------------------------- | ----------------------------------- |
| `wsUnity`    | `ws://<unityHost>:<unityPort>/`  | Unity デバッグ (PCDebug プロトコル) |
| `wsSpatial`  | `ws://<serverHost>:8080/spatial` | Spatial Pipeline                    |
| `wsStatus`   | `ws://<serverHost>:8080/status`  | サーバ状態監視                      |

### 3.2 HTTP クライアント (`$lib/api.ts`)

```typescript
const api = {
  postCommand(body: object): Promise<CommandResponse>;
  postCommandCord(body: object): Promise<CommandResponse>;
  saveGridConfig(payload: object): Promise<{ status: string; filename: string }>;
};
```

### 3.3 ローカルストレージ (`$lib/storage.ts`)

CLI が `saved_grids/` に保存していたファイルはブラウザでは扱えないため:

- **Option A**: ブラウザ IndexedDB に保存し、ダウンロード/アップロード UI を提供
- **Option B**: 軽量なファイルプロキシ API をサーバに追加 (`/api/files/grids`, `/api/files/robots`)

**推奨**: Option B — SystemServer に `/api/files` エンドポイントを追加し、`saved_grids/` を直接読み書き

---

## 4. 画面ワイヤーフレーム

```
┌─────────────────────────────────────────────────────────┐
│ [Unity] [XArm] [Spatial] [Log]          Status: ● 🟢    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  (選択タブの内容がここに表示される)                         │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  接続設定バー                                    │    │
│  │  Unity WS: ws://[____]:8080  [Connect]          │    │
│  │  Server :  http://[____]:8080                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  メイン操作エリア (タブごとに切替)                 │    │
│  │                                                 │    │
│  │                                                 │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  ログ/レスポンスパネル (折り畳み可)               │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## 5. ルーティング

| パス | コンポーネント | 内容                                |
| ---- | -------------- | ----------------------------------- |
| `/`  | `+page.svelte` | ダッシュボード (タブ切替のコンテナ) |

> SPA として `/` 1 ページにタブで全機能を配置する。SvelteKit の SSR は不要のため `ssr: false` に設定。

---

## 6. 主要コンポーネント構成

```
src/
├── lib/
│   ├── ws.ts                    # WebSocket マネージャ
│   ├── api.ts                   # HTTP クライアント
│   ├── storage.ts               # ローカル保存ユーティリティ
│   ├── types.ts                 # 共通型定義
│   └── components/
│       ├── TabContainer.svelte  # タブ切替コンテナ
│       ├── StatusBadge.svelte   # 接続状態バッジ
│       ├── LogPanel.svelte      # ログストリーム
│       ├── JsonViewer.svelte    # JSON 折り畳み表示
│       ├── unity/
│       │   ├── UnityTab.svelte
│       │   ├── CalibrationPanel.svelte
│       │   ├── KeyPad.svelte
│       │   ├── GridFileList.svelte
│       │   ├── FileExplorer.svelte
│       │   └── RawSender.svelte
│       ├── xarm/
│       │   ├── XArmTab.svelte
│       │   ├── BasicControls.svelte
│       │   ├── GripperControls.svelte
│       │   ├── GridPickPanel.svelte
│       │   └── GridMapView.svelte
│       └── spatial/
│           ├── SpatialTab.svelte
│           ├── UtteranceInput.svelte
│           ├── ResultCard.svelte
│           ├── ConfirmationPanel.svelte
│           └── ObjectTable.svelte
└── routes/
    ├── +layout.svelte
    └── +page.svelte
```

---

## 7. 状態管理

Svelte 5 の `$state` / `$derived` を使い、グローバル状態は `lib/` 内のモジュールスコープで管理。

```typescript
// lib/appState.svelte.ts
export const appState = $state({
  activeTab: "unity" as "unity" | "xarm" | "spatial" | "log",

  // 接続先設定
  unityWsUrl: "ws://localhost:8080",
  serverBaseUrl: "http://localhost:8080",

  // 接続状態
  unityConnected: false,
  spatialConnected: false,
  statusConnected: false,
  robotEnabled: false,

  // Spatial フロー状態
  spatialPhase: "idle" as
    | "idle"
    | "processing"
    | "showing_result"
    | "executing",
  lastResult: null as SpatialReferenceResult | null,
  lastTargetId: "" as string,

  // ログ
  logs: [] as LogEntry[],
});
```

---

## 8. CLI → GUI マッピング一覧

| CLI コマンド            | GUI 操作                                   | タブ       |
| ----------------------- | ------------------------------------------ | ---------- |
| `wait`                  | 自動接続 + ステータスバッジ                | 共通ヘッダ |
| `list [recursive]`      | ファイルエクスプローラ ツリービュー        | Unity      |
| `read <path>`           | ツリーのファイルクリック → JSON プレビュー | Unity      |
| `calib <action>`        | Calibration セクションのボタン             | Unity      |
| `key <k>`               | 仮想キーパッド                             | Unity      |
| `restore`               | Grid リスト → Restore ボタン               | Unity      |
| `restore_robot`         | Robot リスト → Restore ボタン              | Unity      |
| `restore_all`           | 「Restore All」ボタン                      | Unity      |
| `grids`                 | Grid ファイルリスト (自動表示)             | Unity      |
| `robots`                | Robot ファイルリスト (自動表示)            | Unity      |
| `import_grid`           | Import Grid ボタン                         | Unity      |
| `import_robot`          | Import Robot ボタン                        | Unity      |
| `import_pair`           | Import Pair ボタン                         | Unity      |
| `legacy <event> <json>` | Raw/Legacy 送信フォーム                    | Unity      |
| `raw <event> <json>`    | Raw/Legacy 送信フォーム                    | Unity      |
| (keyboard_move.py)      | 方向ボタン / グリッドクリック              | XArm       |
| (pick_from_grid.py)     | Grid Map → セルクリック → Pick             | XArm       |
| (対話フロー全般)        | Utterance 入力 → 結果 → 確認               | Spatial    |

---

## 9. 必要なサーバ側拡張 (SystemServer)

現行 SystemServer に以下のエンドポイント追加が必要:

| エンドポイント             | メソッド | 用途                              | 優先度 |
| -------------------------- | -------- | --------------------------------- | ------ |
| `/api/robot/home`          | POST     | xArm Home                         | v1     |
| `/api/robot/initial`       | POST     | xArm Initial Pos                  | v1     |
| `/api/robot/reset`         | POST     | xArm Reset / Recovery             | v1     |
| `/api/robot/gripper`       | POST     | `{ action: "open" \| "close" }`   | v1     |
| `/api/robot/pick`          | POST     | `{ x: int, y: int }`              | v1     |
| `/api/robot/status`        | GET      | 現在位置・エラー状態取得          | v1     |
| `/api/files/grids`         | GET      | ローカル保存済み Grid 一覧        | v1     |
| `/api/files/grids/<name>`  | GET      | Grid JSON 取得                    | v1     |
| `/api/files/robots`        | GET      | ローカル保存済み Robot 一覧       | v1     |
| `/api/files/robots/<name>` | GET      | Robot JSON 取得                   | v1     |
| `/api/robot/jog`           | POST     | `{ dx, dy, dz, step }` 手動ジョグ | v2     |

---

## 10. 開発フェーズ

### Phase 1 — 基盤 + Unity タブ (v0.1)

- [ ] WebSocket マネージャ (`ws.ts`) 実装
- [ ] タブ切替 UI 実装
- [ ] Unity タブ: 接続、キャリブレーション、キー入力、Grid/Robot リストア
- [ ] Log タブ: 全メッセージのストリーム表示

### Phase 2 — Spatial タブ (v0.2)

- [ ] Spatial タブ: 発話入力 → 結果表示 → 確認フィードバック → ロボットコマンドステータス
- [ ] フロー状態管理 (idle → processing → showing_result → executing → idle)

### Phase 3 — XArm タブ (v0.3)

- [ ] SystemServer に `/api/robot/*` エンドポイント追加
- [ ] XArm タブ: 基本操作、グリッパー、グリッドピック
- [ ] Grid Map 可視化

### Phase 4 — 仕上げ (v1.0)

- [ ] エラーハンドリングの統一 (トースト通知)
- [ ] レスポンシブ対応
- [ ] ログのフィルタ / エクスポート
- [ ] 接続先設定の LocalStorage 永続化

---

## 11. 設定

```
# .env (InteractionApp ルート)
VITE_UNITY_WS_URL=ws://localhost:8080
VITE_SERVER_BASE_URL=http://localhost:8080
```

`vite.config.ts` で WebSocket プロキシが必要な場合:

```typescript
server: {
  proxy: {
    '/spatial': { target: 'ws://localhost:8080', ws: true },
    '/status':  { target: 'ws://localhost:8080', ws: true },
    '/api':     { target: 'http://localhost:8080' },
  }
}
```

---

## 12. 技術的制約・備考

- **CORS**: SystemServer 側で CORS を許可する必要がある (`FastAPI CORSMiddleware`)
- **ファイル保存**: ブラウザからファイルシステムに直接書き込めないため、サーバ側ファイル API が必須
- **WakeWord / 音声認識**: Unity/HoloLens デバイス上でのみ動作。Web アプリ側では再現しない (テキスト入力で代替)
- **Svelte 5**: `$state`, `$derived`, `$effect` を活用。レガシーな `writable` store は使用しない
