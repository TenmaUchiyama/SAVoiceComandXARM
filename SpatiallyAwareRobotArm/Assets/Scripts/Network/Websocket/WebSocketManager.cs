using System;
using System.Collections.Generic;
using UnityEngine;
using NativeWebSocket; // GitHubから導入が必要
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using TMPro;
using System.Threading.Tasks;


namespace SA_XARM.Network.Websocket{


[Serializable]
public class WSPacket
{
    public string eventId; // イベント名（例: "OnMove", "OnLogin"）
    public string payload; // 中身のJSON文字列
}



public class WebSocketManager : MonoBehaviour
{
    public static WebSocketManager Instance { get; private set; }

    public bool IsConnected => _websocket != null && _websocket.State == WebSocketState.Open;

    [Header("Settings")]
    [SerializeField] private string serverAddress = "192.168.108.164";
    [SerializeField] private string serverPort = "8080";
    [SerializeField] private string spatialPath = "/spatial";
    [SerializeField] private bool autoConnectOnStart = false; // ← 自動接続スイッチ
    [SerializeField] private float reconnectIntervalSeconds = 2f;

    
    [SerializeField] private TextMeshProUGUI socketConnectedStatusText; 

    private WebSocket _websocket;
    private Dictionary<string, Action<string>> _handlers = new Dictionary<string, Action<string>>();
    private string serverUrl;
    private bool _manualDisconnectRequested;
    private bool _isQuitting;
    private bool _isReconnecting;

    private void SetStatusText(string text)
    {
        if (socketConnectedStatusText == null) return;
        socketConnectedStatusText.text = text;
    }

    private void Awake()
    {
        if (Instance == null)
        {
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }
        else
        {
            Destroy(gameObject);
        }
        string normalizedPath = string.IsNullOrWhiteSpace(spatialPath) ? "/spatial" : spatialPath.Trim();
        if (!normalizedPath.StartsWith("/")) normalizedPath = "/" + normalizedPath;
        serverUrl = $"ws://{serverAddress}:{serverPort}{normalizedPath}";
    }

    private void Start()
    {
        SetStatusText("Disconnected");

        // チェックが入っている時だけ自動接続
        if (autoConnectOnStart)
        {
            Connect();
        }
    }

    void Update()
    {
        #if !UNITY_WEBGL || UNITY_EDITOR
            // 接続中のみディスパッチを実行
            if (_websocket != null)
            {
                if (_websocket.State == WebSocketState.Open)
                {
                    _websocket.DispatchMessageQueue();
                }
                else
                {
                    // 接続状態を定期的に確認（1秒ごと）
                    if (Time.frameCount % 60 == 0)
                    {
                        SpatialDebugLog.Instance.Log($"[WS] Current state: {_websocket.State}", true, "yellow");
                     
                    }
                }
            }
        #endif
    }

    private async void OnApplicationQuit()
    {
        _isQuitting = true;
        _manualDisconnectRequested = true;
        await Disconnect();
    }

    // =================================================================
    // ▼ 公開メソッド（ボタンからここを呼ぶ）
    // =================================================================

    /// <summary>
    /// サーバーに接続開始
    /// </summary>
    public async void Connect()
    {
        _manualDisconnectRequested = false;
        await ConnectInternal();
    }

    private async Task ConnectInternal()
    {
        // 既に接続中なら何もしない（連打防止）
        if (_websocket != null && 
           (_websocket.State == WebSocketState.Open || _websocket.State == WebSocketState.Connecting))
        {
            SpatialDebugLog.Instance.LogError("Already connected or connecting.");
            SetStatusText(_websocket.State == WebSocketState.Open ? "Connected" : "Connecting");
            return;
        }

        SpatialDebugLog.Instance.Log($"[WS] Connecting to {serverUrl}...", true, "white");
        SetStatusText("Connecting");
        
        // インスタンスを生成（再接続時にも新しく作る必要がある）
        _websocket = new WebSocket(serverUrl);
        var currentSocket = _websocket;

        // イベント定義
        _websocket.OnOpen += () => {
            SpatialDebugLog.Instance.Log("[WS] Connected!", true, "green");
            SetStatusText("Connected");
            _isReconnecting = false;
            RegisterBuiltInHandlers();
            SpatialDebugLog.Instance.Log($"[WS] State: {currentSocket.State}", true, "white");
        };
        _websocket.OnError += (e) =>
        {
            SpatialDebugLog.Instance.LogError("WS Error: " + e);
            SetStatusText("Error");
        };
        _websocket.OnClose += (e) =>
        {
            SpatialDebugLog.Instance.Log("[WS] Closed: " + e, true, "yellow");
            SetStatusText("Disconnected");

            if (ReferenceEquals(_websocket, currentSocket))
            {
                _websocket = null;
            }

            if (!_manualDisconnectRequested && !_isQuitting)
            {
                _ = ReconnectLoop();
            }
        };
        
        // メッセージ受信処理
        _websocket.OnMessage += (bytes) =>
        {
            var json = System.Text.Encoding.UTF8.GetString(bytes);
            try 
            {
                string eventId = null;
                string payload = json;

                var token = JToken.Parse(json);
                if (token is JObject obj)
                {
                    // legacy packet: { eventId, payload }
                    if (obj.TryGetValue("eventId", out var legacyEventToken))
                    {
                        eventId = legacyEventToken?.ToString()?.Trim();
                        payload = obj.TryGetValue("payload", out var payloadToken)
                            ? payloadToken?.ToString()
                            : "{}";
                    }
                    // /spatial raw response: { type, ... }
                    else if (obj.TryGetValue("type", out var typeToken))
                    {
                        eventId = typeToken?.ToString()?.Trim();
                        payload = json;
                    }
                }

                SpatialDebugLog.Instance.Log($"[WS] Received event '{eventId}'", true, "white");

                if (!string.IsNullOrEmpty(eventId) && _handlers.ContainsKey(eventId))
                {
                    try
                    {
                        _handlers[eventId]?.Invoke(payload);
                    }
                    catch (Exception ex)
                    {
                        SpatialDebugLog.Instance.Log($"[WS] Handler error for eventId='{eventId}': {ex}", true, "red");
                    }
                }
                else
                {
                     SpatialDebugLog.Instance.Log($"[WS]No handler for eventId: '{eventId}'", true, "yellow");
                    SpatialDebugLog.Instance.Log($"[WS] Available handlers: {string.Join(", ", _handlers.Keys)}", true, "yellow");
                }
            }
            catch (Exception)
            {
                // SpatialDebugLog.Instance.Log($"[WS]Parse Error: {e.Message}\n{e.StackTrace}", true, "red");
            }
        };

        // 実際に接続
        try
        {
            await _websocket.Connect();
        }
        catch (Exception e)
        {
            SpatialDebugLog.Instance.Log("[WS]Connect failed: " + e.Message, true, "red");
            SetStatusText("Error");

            if (!_manualDisconnectRequested && !_isQuitting)
            {
                _ = ReconnectLoop();
            }
        }
    }

    private async Task ReconnectLoop()
    {
        if (_isReconnecting || _manualDisconnectRequested || _isQuitting) return;

        _isReconnecting = true;
        SpatialDebugLog.Instance.Log("[WS] Reconnect loop started.", true, "yellow");

        while (!_manualDisconnectRequested && !_isQuitting && !IsConnected)
        {
            SetStatusText("Reconnecting...");
            SpatialDebugLog.Instance.Log($"[WS] Reconnecting in {reconnectIntervalSeconds:F1}s...", true, "yellow");

            await Task.Delay(TimeSpan.FromSeconds(reconnectIntervalSeconds));

            if (_manualDisconnectRequested || _isQuitting || IsConnected)
            {
                break;
            }

            await ConnectInternal();
        }

        if (!IsConnected)
        {
            SetStatusText("Disconnected");
        }

        _isReconnecting = false;
    }

    /// <summary>
    /// 切断（切断ボタン用）
    /// </summary>
    public async System.Threading.Tasks.Task Disconnect()
    {
        _manualDisconnectRequested = true;
        _isReconnecting = false;

        if (_websocket != null)
        {
            await _websocket.Close();
            _websocket = null;
            Debug.Log("Disconnected.");
            SetStatusText("Disconnected");
        }
        else
        {
            SetStatusText("Disconnected");
        }
    }

    // ... Send, On, Off メソッドは変更なし（前のコードのまま） ...
     public void Send<T>(string eventId, T data)
    {
        if (_websocket == null || _websocket.State != WebSocketState.Open) return;
        SpatialDebugLog.Instance.Log($"[WS] Sending event '{eventId}'", true, "cyan");

        string jsonPayload = JsonConvert.SerializeObject(data);
        JObject payloadObj;
        try
        {
            payloadObj = JObject.Parse(jsonPayload);
        }
        catch
        {
            payloadObj = new JObject();
        }

        if (!payloadObj.ContainsKey("type") && !string.IsNullOrWhiteSpace(eventId))
        {
            payloadObj["type"] = eventId;
        }

        _websocket.SendText(payloadObj.ToString(Formatting.None));
        
        #if !UNITY_WEBGL || UNITY_EDITOR
            // 送信後に即座にメッセージキューを処理
            _websocket.DispatchMessageQueue();
        #endif
    }

    // 生のJSON文字列をそのまま受け取る版（デバッグ用）
    public void On(string eventId, Action<string> callback)
    {
        string key = (eventId ?? string.Empty).Trim();
        if (string.IsNullOrEmpty(key)) return;
        if (_handlers.ContainsKey(key)) _handlers.Remove(key);
        _handlers.Add(key, callback);
    }

    // 型解析して受け取る版
    public void On<T>(string eventId, Action<T> callback)
    {
        string key = (eventId ?? string.Empty).Trim();
        if (string.IsNullOrEmpty(key)) return;
        if (_handlers.ContainsKey(key)) _handlers.Remove(key);
        _handlers.Add(key, (jsonPayload) => {
            T data = JsonConvert.DeserializeObject<T>(jsonPayload);
            callback(data);
        });
    }

    public void Off(string eventId)
    {
        string key = (eventId ?? string.Empty).Trim();
        if (string.IsNullOrEmpty(key)) return;
        if (_handlers.ContainsKey(key)) _handlers.Remove(key);
    }

    /// <summary>
    /// Register built-in transport-level handlers (e.g. KeepAlive).
    /// Called automatically after connection is established.
    /// </summary>
    private void RegisterBuiltInHandlers()
    {
        On("KeepAlive", (string _) => { /* server keep-alive ping — no action needed */ });
    }

        internal async Task<string> SendPickGridRequest(int x_grid, int y_grid)
        {
            SpatialDebugLog.Instance.Log(
                "<color=yellow>[WebSocketManager] XarmPick over WS is removed. Use spatial flow (/spatial) confirmation path.</color>",
                true
            );
            await Task.CompletedTask;
            return "unsupported";
        }
    }
}