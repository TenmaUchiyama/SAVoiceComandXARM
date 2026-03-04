# Unity アプリ設計書 | Spatial Referring System

**User-Centric Spatial Referring for Tabletop Robot Manipulation with MR Grounding and LLMs**

- **バージョン**: 1.1
- **作成日**: 2026-03-02
- **対象プラットフォーム**: HoloLens 2 (UWP / ARM64)
- **Unity バージョン**: 2022.3 LTS 以上

---

## 目次

1. [システム概要](#1-システム概要)
2. [アーキテクチャ概観](#2-アーキテクチャ概観)
3. [シーン構成](#3-シーン構成)
4. [コンポーネント設計](#4-コンポーネント設計)
   - 4.1 [通信層: WebSocketClient](#41-通信層-websocketclient)
   - 4.2 [空間理解層: SpatialContextProvider](#42-空間理解層-spatialcontextprovider)
   - 4.3 [音声入力層: VoiceCommandHandler](#43-音声入力層-voicecommandhandler)
   - 4.4 [アプリ状態管理: AppStateManager](#44-アプリ状態管理-appstatemanager)
   - 4.5 [MR 表示層: MRVisualizationManager](#45-mr-表示層-mrvisualizationmanager)
   - 4.6 [物体管理: ObjectRegistry](#46-物体管理-objectregistry)
   - 4.7 [ロボット連携: RobotCommandHandler](#47-ロボット連携-robotcommandhandler)
   - 4.8 [空間物体コンポーネント: SpatialObject](#48-空間物体コンポーネント-spatialobject)
5. [アプリ状態遷移](#5-アプリ状態遷移)
6. [送受信メッセージの組み立て](#6-送受信メッセージの組み立て)
7. [QR グリッドによる物体位置取得](#7-qr-グリッドによる物体位置取得)
8. [UI / UX 設計](#8-ui--ux-設計)
9. [ディレクトリ構成](#9-ディレクトリ構成)
10. [設定・定数管理](#10-設定定数管理)
11. [エラーハンドリング](#11-エラーハンドリング)

---

## 1. システム概要

Unity アプリは **HoloLens 2** 上で動作する MR フロントエンドである。役割は以下の通り。

| 責務             | 詳細                                                       |
| ---------------- | ---------------------------------------------------------- |
| 空間データ収集   | ユーザー姿勢・物体位置・ロボット位置をテーブル座標系で取得 |
| 音声入力         | MRTK の音声認識で発話をテキスト化し LLM サーバーへ送信     |
| 推論結果の可視化 | サーバーから返ってきたターゲット候補を MR ホログラムで表示 |
| ユーザー確認     | 音声または視線 + エアタップで物体選択を確認                |
| リファインメント | 不一致時に修正発話を再送信                                 |
| ロボット指令受信 | `robot_command` を受け取りアーム動作ステータスを表示       |

---

## 2. アーキテクチャ概観

```
HoloLens 2 (Unity)
┌────────────────────────────────────────────────────────┐
│  VoiceCommandHandler                                   │
│    └─── MRTK SpeechInputHandler                       │
│                                                        │
│  SpatialContextProvider                                │
│    ├─── UserPoseTracker (Camera Transform)            │
│    ├─── ObjectRegistry (QR Grid + Anchor)             │
│    └─── RobotPoseTracker (Static / QR Anchor)         │
│                                                        │
│  AppStateManager  ←──────────────────────────────┐   │
│    └── ステート遷移・イベントバス                        │   │
│                                                   │   │
│  WebSocketClient  ─── ws://<server>:8765/spatial  │   │
│    ├─── Send: spatial_reference_request           │   │
│    ├─── Send: refinement_request                  │   │
│    ├─── Send: confirmation                        │   │
│    ├─── Recv: spatial_reference_result ───────────┘   │
│    └─── Recv: robot_command                           │
│                                                        │
│  MRVisualizationManager                               │
│    ├─── ObjectHighlighter (候補ハイライト)              │
│    ├─── ConfirmationUI (確認パネル)                    │
│    └─── StatusHUD (処理中・エラー表示)                 │
│                                                        │
│  RobotCommandHandler                                   │
│    └─── ロボット動作ステータス表示                       │
└────────────────────────────────────────────────────────┘
```

---

## 3. シーン構成

### 推奨シーン

| シーン名    | 用途                               |
| ----------- | ---------------------------------- |
| `Bootstrap` | 設定読み込み・接続確立・シーン遷移 |
| `Main`      | メインの MR 操作シーン             |

### Main シーン内 GameObject 階層

```
[Scene Root]
├── MRTK XR Rig                    # HoloLens カメラ + 入力
│   └── Main Camera
├── Managers                       # 各マネージャーの空 GameObject
│   ├── AppStateManager
│   ├── WebSocketClient
│   ├── SpatialContextProvider
│   ├── VoiceCommandHandler
│   ├── ObjectRegistry
│   ├── MRVisualizationManager
│   └── RobotCommandHandler
├── ObjectHologramsRoot            # 物体ホログラムの親
└── UI
    ├── StatusHUD
    └── ConfirmationPanel
```

---

## 4. コンポーネント設計

### 4.1 通信層: `WebSocketClient`

WebSocket 接続を管理し、JSON メッセージの送受信と再接続ロジックを担う。

```csharp
public class WebSocketClient : MonoBehaviour
{
    [SerializeField] private string serverUrl = "ws://192.168.1.100:8765/spatial";

    // 送信
    public async Task SendAsync(string jsonMessage);

    // イベント
    public event Action<string> OnMessageReceived;
    public event Action OnConnected;
    public event Action OnDisconnected;

    // 自動再接続（最大 5 回、指数バックオフ）
    private async Task ReconnectAsync();
}
```

**実装方針**

- `NativeWebSocket` または `WebSocketSharp` ライブラリを使用（UWP 対応）
- `UnityMainThreadDispatcher` で受信コールバックをメインスレッドに移送
- 切断時はセッション ID を保持し再接続後に継続可能

---

### 4.2 空間理解層: `SpatialContextProvider`

LLM サーバーへ送信する空間情報を組み立てて提供する。

```csharp
public class SpatialContextProvider : MonoBehaviour
{
    // ユーザー姿勢（HoloLens カメラ Transform）
    public UserPose GetUserPose();

    // ロボット姿勢（QR アンカー or 手動設定）
    public RobotPose GetRobotPose();

    // 全物体の現在位置リスト
    public List<ObjectData> GetObjects();

    // 完全なリクエスト DTO を組み立てる
    public SpatialReferenceRequest BuildRequest(string utteranceText, string language = "ja");
}
```

---

### 4.3 音声入力層: `VoiceCommandHandler`

MRTK の音声認識を利用し、連続発話をキャプチャしてパイプラインを起動する。

```csharp
public class VoiceCommandHandler : MonoBehaviour
{
    // 常時リッスン（プッシュトゥトーク or 常時）
    [SerializeField] private bool continuousListen = true;

    // 発話確定時イベント
    public event Action<string> OnUtteranceRecognized;

    // MRTK ISpeechHandler 経由、または Windows.Media.SpeechRecognition 直接使用
}
```

**フロー**

1. 音声認識が発話テキストを返す
2. `AppStateManager.OnUtteranceReceived(text)` を呼び出す
3. `AppStateManager` が `SpatialContextProvider.BuildRequest()` でリクエストを組み立て
4. `WebSocketClient.SendAsync(json)` で送信

---

### 4.4 アプリ状態管理: `AppStateManager`

アプリ全体のステートマシンを管理し、各コンポーネント間のイベントを仲介する。

```csharp
public enum AppState
{
    Idle,           // 待機中
    Listening,      // 音声入力受付中
    Processing,     // LLM 推論待ち
    ShowingResult,  // 候補表示中（ユーザー確認待ち）
    Refining,       // リファインメント発話待ち
    Executing,      // ロボット動作中
    Error           // エラー表示
}

public class AppStateManager : MonoBehaviour
{
    public AppState CurrentState { get; private set; }

    public void OnUtteranceReceived(string text);
    public void OnResultReceived(SpatialReferenceResult result);
    public void OnUserConfirmed(string objectId);
    public void OnUserRefined(string refinementText);
    public void OnRobotCommandReceived(RobotCommand cmd);
}
```

---

### 4.5 MR 表示層: `MRVisualizationManager`

LLM 推論結果をホログラムとして可視化する。

```csharp
public class MRVisualizationManager : MonoBehaviour
{
    // 上位スコアの物体をハイライト表示
    public void ShowCandidates(List<RankedCandidate> candidates);

    // ターゲット物体を強調（確認パネル表示）
    public void ShowConfirmationFor(string objectId, string reasoning);

    // 全ハイライトをクリア
    public void ClearHighlights();

    // HUD にメッセージを表示
    public void ShowStatus(string message, StatusType type);
}
```

**可視化方針**

| 状態         | 表示                                         |
| ------------ | -------------------------------------------- |
| 候補 Top 1   | 緑色の枠 + スコア（例: 92%）                 |
| 候補 Top 2〜 | 黄色の半透明枠                               |
| 確認パネル   | 物体名・理由・「はい」「いいえ」音声コマンド |
| 処理中       | ローディングスピナー（StatusHUD）            |
| エラー       | 赤色のアラートバナー                         |

---

### 4.6 物体管理: `ObjectRegistry`

テーブル上に配置された物体の位置・属性を管理する。

```csharp
public class ObjectRegistry : MonoBehaviour
{
    // QR グリッドスキャン結果から物体を登録
    public void RegisterFromGridConfig(GridConfig config);

    // 物体リストの取得
    public List<ObjectData> GetAll();

    // 物体 ID で GameObject を検索（ハイライト用）
    public GameObject FindHologram(string objectId);
}
```

**物体位置の取得方法**（既存 QR グリッド構成を流用）

- `qr_grid_config.json` の各セルに対応した QR コードを HoloLens が検出
- 各セルの `WorldAnchor` からテーブル座標系上の位置を算出
- MR オーバーレイ（ラベル・カラー情報）を付与してホログラムとして表示

---

### 4.7 ロボット連携: `RobotCommandHandler`

サーバーから受信した `robot_command` をもとに、ロボットの動作状態を追跡・表示する。

```csharp
public class RobotCommandHandler : MonoBehaviour
{
    public void HandleCommand(RobotCommand cmd);

    // ロボットアーム方向への矢印ホログラム表示
    private void ShowReachArrow(Vector3 targetPosition);

    // 動作ステータスを HUD に表示
    private void UpdateStatusDisplay(string status);
}
```

## 4.8 空間物体コンポーネント: `SpatialObject`

各物体ホログラム GameObject にアタッチするコンポーネント。物体の属性データを保持し、ハイライト制御・空間計算などのユーティリティを提供する。`ObjectRegistry` を経由せずに直接アクセスできるため、レイキャストやエアタップのヒット時の処理がシンプルになる。

#### 属性パラメータ

```csharp
[RequireComponent(typeof(MeshRenderer))]
public class SpatialObject : MonoBehaviour
{
    // --- 識別 ---
    public string Id { get; private set; }          // "obj_001"

    // --- 視覚属性 ---
    public string Label { get; private set; }    // "bottle" / "box" など
    public string Color { get; private set; }    // "red" / "blue" など

    // --- 空間属性 ---
    public Vector3 Position { get; private set; }   // テーブル座標系での位置

    // --- 状態 ---
    public bool IsHighlighted { get; private set; }
}

```

#### 初期化

```csharp
// ObjectRegistry から呼び出す
public void Initialize(ObjectData data)
{
    Id       = data.id;
    Label    = data.label;
    Color    = data.color;
    Position = data.position.ToVector3();
}
```

#### ハイライト制御

```csharp
// MRVisualizationManager から呼び出す
public void Highlight();    // マテリアルをハイライト色に切り替え
public void Unhighlight();  // マテリアルをデフォルトに戻す
```

#### ラベル表示

```csharp
public void ShowLabel(string overrideText = null);  // 引数なしなら Label を表示
public void HideLabel();
```

#### 空間ユーティリティ

```csharp
// ビューワー（ユーザー視点）から見た相対方向を返す
// LLM への空間記述生成や候補フィルタリングに使用する
// 例: "left" / "right" / "front" / "back" / "front-left" など
public string GetDirectionFrom(Vector3 viewerPosition, Vector3 viewerForward);

// 指定点との距離を返す（テーブル座標系）
public float GetDistanceTo(Vector3 point);

// ロボットのリーチ圏内かどうかを判定する
public bool IsReachableBy(Vector3 robotPosition, float reachRadius);

// サーバー送信用 DTO に変換する
public ObjectData ToObjectData();
```

**`GetDirectionFrom` の使いどころ**

`SpatialContextProvider.BuildRequest()` 内で各物体に対して呼び出し、`ObjectData` に `relative_direction` フィールドとして付与することで、LLM が「ユーザーから見て左側にある赤いボトル」のような表現を正確に解釈しやすくなる。

---

## 5. アプリ状態遷移

```
                  アプリ起動
                      │
                   Idle ◄────────────────────────────────────┐
                      │                                       │
              音声入力検出                              完了 / キャンセル
                      │                                       │
                 Listening                                     │
                      │                                       │
              発話テキスト確定                                  │
                      │                                       │
                 Processing ──── LLM タイムアウト ──► Error ──┘
                      │
              spatial_reference_result 受信
                      │
                ShowingResult
                ┌─────┴─────┐
           「はい」確認     「違う」修正
                │               │
           Executing         Refining
                │               │
      robot_command 受信    修正発話確定
                │               │
      ステータス表示          Processing
                │
              Idle に戻る
```

---

## 6. 送受信メッセージの組み立て

### `spatial_reference_request` の組み立て

```csharp
// SpatialContextProvider.BuildRequest() の内部処理
var request = new SpatialReferenceRequest
{
    type = "spatial_reference_request",
    request_id = System.Guid.NewGuid().ToString(),
    timestamp = System.DateTime.UtcNow.ToString("o"),
    utterance = new Utterance { text = utteranceText, language = "ja" },
    user_pose = GetUserPose(),   // カメラ Transform から変換
    objects = GetObjects(),      // ObjectRegistry から取得
    robot_pose = GetRobotPose()  // ロボット QR アンカー
};
return JsonUtility.ToJson(request);
```

### `confirmation` の組み立て

```csharp
var confirmation = new ConfirmationMessage
{
    type = "confirmation",
    request_id = System.Guid.NewGuid().ToString(),
    confirmed_object_id = selectedObjectId,
    action = "pick"
};
```

### `refinement_request` の組み立て

```csharp
var refinement = new RefinementRequest
{
    type = "refinement_request",
    request_id = System.Guid.NewGuid().ToString(),
    original_request_id = _lastRequestId,
    utterance = new Utterance { text = refinementText, language = "ja" },
    user_pose = GetUserPose(),
    previous_target = _lastTargetObjectId
};
```

### 受信メッセージのルーティング

```csharp
// WebSocketClient.OnMessageReceived から呼び出す
void RouteMessage(string json)
{
    var msg = JsonUtility.FromJson<BaseMessage>(json);
    switch (msg.type)
    {
        case "spatial_reference_result":
            var result = JsonUtility.FromJson<SpatialReferenceResult>(json);
            appStateManager.OnResultReceived(result);
            break;
        case "robot_command":
            var cmd = JsonUtility.FromJson<RobotCommand>(json);
            robotCommandHandler.HandleCommand(cmd);
            break;
    }
}
```

---

## 7. QR グリッドによる物体位置取得

既存の `qr_grid_config.json` を活用し、テーブル上の物体位置をサーバー側データと同期する。

### フロー

```
1. アプリ起動後、テーブル上の QR コードを HoloLens でスキャン
2. QR コード ID と grid_pose_map.json を照合してセル位置を特定
3. 各セルに物体ホログラム (ラベル + バウンディングボックス) を配置
```

### `ObjectData` の構造（サーバー送信用）

```csharp
[Serializable]
public class ObjectData
{
    public string id;                   // "obj_001"
    public string label;                // "bottle"
    public string color;                // "red"
    public string shape;                // "cylinder"
    public string size;                 // "small" / "medium" / "large"
    public Vec3   position;             // テーブル座標系
    public string relative_direction;   // "left" / "front-right" など（SpatialObject.GetDirectionFrom() で算出）
}
```

---

## 8. UI / UX 設計

### 音声コマンド一覧

| 発話                             | アクション                            |
| -------------------------------- | ------------------------------------- |
| 任意の自然文発話                 | `spatial_reference_request` を送信    |
| 「はい」「そう」「合ってる」     | `confirmation` を送信（action: pick） |
| 「違う」「別のやつ」「もっと〜」 | `refinement_request` を送信           |
| 「キャンセル」「やめて」         | `Idle` 状態に戻る                     |

### StatusHUD の表示内容

| 状態          | 表示メッセージ例            |
| ------------- | --------------------------- |
| Listening     | 🎤 聞いています...          |
| Processing    | ⏳ 推論中...                |
| ShowingResult | ✅ 対象: 赤いボックス (92%) |
| Executing     | 🤖 ロボット動作中           |
| Error         | ⚠️ エラー: タイムアウト     |

### 候補物体の可視化

- **Top 1 候補**: 緑色のアウトライン + "Target (92%)" ラベル
- **Top 2 以降**: 黄色の半透明アウトライン
- **確認パネル**: 物体の上に「これですか？」とテキストを浮かべる
- **Reasoning 表示**: 確認パネルに推論根拠テキスト（例: "ユーザー視点で右側かつ赤色"）を表示

---

## 9. ディレクトリ構成

```
Assets/
├── Scripts/
│   ├── Network/
│   │   ├── WebSocketClient.cs
│   │   └── MessageRouter.cs
│   ├── Spatial/
│   │   ├── SpatialContextProvider.cs
│   │   ├── UserPoseTracker.cs
│   │   ├── ObjectRegistry.cs
│   │   └── QRGridScanner.cs
│   ├── Voice/
│   │   └── VoiceCommandHandler.cs
│   ├── State/
│   │   └── AppStateManager.cs
│   ├── Visualization/
│   │   ├── MRVisualizationManager.cs
│   │   ├── ObjectHighlighter.cs
│   │   └── StatusHUD.cs
│   ├── Robot/
│   │   └── RobotCommandHandler.cs
│   └── Data/
│       ├── Messages/               # 送受信 DTO
│       │   ├── SpatialReferenceRequest.cs
│       │   ├── SpatialReferenceResult.cs
│       │   ├── RefinementRequest.cs
│       │   ├── ConfirmationMessage.cs
│       │   └── RobotCommand.cs
│       └── GridConfig.cs
├── Prefabs/
│   ├── ObjectHologram.prefab       # 物体可視化用
│   ├── ConfirmationPanel.prefab
│   └── StatusHUD.prefab
├── Scenes/
│   ├── Bootstrap.unity
│   └── Main.unity
└── Resources/
    └── qr_grid_config.json         # サーバー側と共有
```

---

## 10. 設定・定数管理

```csharp
// Assets/Scripts/Config/AppConfig.cs
[CreateAssetMenu]
public class AppConfig : ScriptableObject
{
    [Header("Network")]
    public string serverHost = "192.168.1.100";
    public int serverPort = 8765;
    public float reconnectIntervalSec = 3.0f;
    public int maxReconnectAttempts = 5;

    [Header("Session")]
    public float sessionTimeoutSec = 300.0f;

    [Header("Voice")]
    public bool continuousListen = true;
    public string language = "ja-JP";

    [Header("Visualization")]
    public Color topCandidateColor = Color.green;
    public Color otherCandidateColor = Color.yellow;
}
```

---

## 11. エラーハンドリング

| サーバーエラーコード      | Unity 側の対応                                                     |
| ------------------------- | ------------------------------------------------------------------ |
| E001 (LLM タイムアウト)   | StatusHUD に「タイムアウト、もう一度試してください」表示し Idle へ |
| E002 (パース失敗)         | StatusHUD に「認識失敗」表示し Idle へ                             |
| E003 (物体なし)           | StatusHUD に「テーブル上に物体が検出されません」表示               |
| E004 (無効座標)           | 再スキャンを促すガイド表示                                         |
| E005 (WS 切断)            | 自動再接続、接続中は Processing スピナー継続                       |
| E006 (セッション期限切れ) | Bootstrap シーンに戻り再初期化                                     |

### 接続失敗時のフォールバック

- サーバーに未接続の間は音声認識ボタンを無効化
- StatusHUD に「サーバーに接続中...」を常時表示
- QR スキャンは接続と独立して実行可能

---

## 依存ライブラリ・パッケージ

| パッケージ                             | 用途                                                     |
| -------------------------------------- | -------------------------------------------------------- |
| MRTK3 (Mixed Reality Toolkit)          | HoloLens 入力・UI・音声認識                              |
| Microsoft.MixedReality.QR              | QR コード検出                                            |
| NativeWebSocket または websocket-sharp | WebSocket 通信                                           |
| Newtonsoft.Json (Json.NET)             | JSON シリアライズ（`JsonUtility` の代替として推奨）      |
| UnityMainThreadDispatcher              | WebSocket スレッドからメインスレッドへのコールバック移送 |
