using System;
using System.Collections.Generic;
using UnityEngine;
using NativeWebSocket;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using System.Threading.Tasks;

namespace SA_XARM.Network.Websocket
{
    /// <summary>
    /// InteractionApp Debug Server (port 8765) 用の WebSocket クライアント。
    /// WebSocketManager (port 8080/spatial) とは独立して動作する。
    /// PCDebuggerWebSocket などのデバッグ系コンポーネントはこちらを使う。
    /// </summary>
    public class DebugWebSocketClient : MonoBehaviour
    {
        public static DebugWebSocketClient Instance { get; private set; }

        public bool IsConnected => _websocket != null && _websocket.State == WebSocketState.Open;

        [Header("Debug Server Settings")]
        [SerializeField] private string serverAddress = "192.168.108.164";
        [SerializeField] private string serverPort = "8765";
        [SerializeField] private string wsPath = "/";
        [SerializeField] private bool autoConnectOnStart = false;
        [SerializeField] private float reconnectIntervalSeconds = 3f;

        private WebSocket _websocket;
        private Dictionary<string, Action<string>> _handlers = new Dictionary<string, Action<string>>();
        private string _serverUrl;
        private bool _manualDisconnectRequested;
        private bool _isQuitting;
        private bool _isReconnecting;

        // ================================================================
        // ▼ ライフサイクル
        // ================================================================

        private void Awake()
        {
            if (Instance == null)
            {
                Instance = this;
                // DontDestroyOnLoad は WebSocketManager 側の GameObject で管理されるため不要
                // （同じ GameObject に付ける場合は重複しないようにする）
            }
            else
            {
                Destroy(this);
                return;
            }

            string normalizedPath = string.IsNullOrWhiteSpace(wsPath) ? "/" : wsPath.Trim();
            if (!normalizedPath.StartsWith("/")) normalizedPath = "/" + normalizedPath;
            _serverUrl = $"ws://{serverAddress}:{serverPort}{normalizedPath}";
        }

        private void Start()
        {
            if (autoConnectOnStart)
            {
                Connect();
            }
        }

        private void Update()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            if (_websocket != null && _websocket.State == WebSocketState.Open)
            {
                _websocket.DispatchMessageQueue();
            }
#endif
        }

        private async void OnApplicationQuit()
        {
            _isQuitting = true;
            _manualDisconnectRequested = true;
            await Disconnect();
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
        }

        // ================================================================
        // ▼ 公開メソッド
        // ================================================================

        /// <summary>接続開始（ボタン / スクリプトから呼ぶ）</summary>
        public async void Connect()
        {
            _manualDisconnectRequested = false;
            await ConnectInternal();
        }

        /// <summary>切断</summary>
        public async Task Disconnect()
        {
            _manualDisconnectRequested = true;
            _isReconnecting = false;

            if (_websocket != null)
            {
                await _websocket.Close();
                _websocket = null;
                Log("[DebugWS] Disconnected.", "yellow");
            }
        }

        /// <summary>イベント送信（legacy WSPacket 形式）</summary>
        public void Send<T>(string eventId, T data)
        {
            if (_websocket == null || _websocket.State != WebSocketState.Open) return;

            Log($"[DebugWS] Sending '{eventId}'", "cyan");

            // サーバーが legacy 形式（eventId + payload）を受け付けるので、そちらで送る
            var packet = new WSPacket
            {
                eventId = eventId,
                payload = JsonConvert.SerializeObject(data)
            };
            _websocket.SendText(JsonConvert.SerializeObject(packet));

#if !UNITY_WEBGL || UNITY_EDITOR
            _websocket.DispatchMessageQueue();
#endif
        }

        /// <summary>生 JSON 文字列でハンドラ登録</summary>
        public void On(string eventId, Action<string> callback)
        {
            string key = (eventId ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(key)) return;
            _handlers[key] = callback;
        }

        /// <summary>型付きハンドラ登録</summary>
        public void On<T>(string eventId, Action<T> callback)
        {
            string key = (eventId ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(key)) return;
            _handlers[key] = (json) =>
            {
                T data = JsonConvert.DeserializeObject<T>(json);
                callback(data);
            };
        }

        /// <summary>ハンドラ解除</summary>
        public void Off(string eventId)
        {
            string key = (eventId ?? string.Empty).Trim();
            if (!string.IsNullOrEmpty(key)) _handlers.Remove(key);
        }

        // ================================================================
        // ▼ 内部
        // ================================================================

        private async Task ConnectInternal()
        {
            if (_websocket != null &&
               (_websocket.State == WebSocketState.Open || _websocket.State == WebSocketState.Connecting))
            {
                Log("[DebugWS] Already connected or connecting.", "yellow");
                return;
            }

            Log($"[DebugWS] Connecting to {_serverUrl}...", "white");

            _websocket = new WebSocket(_serverUrl);
            var currentSocket = _websocket;

            _websocket.OnOpen += () =>
            {
                Log("[DebugWS] Connected!", "green");
                _isReconnecting = false;
                // KeepAlive 自動応答
                On("KeepAlive", (string _) => { });
            };

            _websocket.OnError += (e) =>
            {
                Log("[DebugWS] Error: " + e, "red");
            };

            _websocket.OnClose += (e) =>
            {
                Log("[DebugWS] Closed: " + e, "yellow");

                if (ReferenceEquals(_websocket, currentSocket))
                {
                    _websocket = null;
                }

                if (!_manualDisconnectRequested && !_isQuitting)
                {
                    _ = ReconnectLoop();
                }
            };

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
                        // legacy: { eventId, payload }
                        if (obj.TryGetValue("eventId", out var legacyEv))
                        {
                            eventId = legacyEv?.ToString()?.Trim();
                            payload = obj.TryGetValue("payload", out var pToken)
                                ? pToken?.ToString()
                                : "{}";
                        }
                        // raw: { type, ... }
                        else if (obj.TryGetValue("type", out var typeToken))
                        {
                            eventId = typeToken?.ToString()?.Trim();
                            payload = json;
                        }
                    }

                    if (!string.IsNullOrEmpty(eventId) && _handlers.TryGetValue(eventId, out var handler))
                    {
                        try
                        {
                            handler.Invoke(payload);
                        }
                        catch (Exception ex)
                        {
                            Log($"[DebugWS] Handler error '{eventId}': {ex.Message}", "red");
                        }
                    }
                    else
                    {
                        Log($"[DebugWS] No handler for '{eventId}'", "yellow");
                    }
                }
                catch (Exception)
                {
                    // パース失敗は無視
                }
            };

            try
            {
                await _websocket.Connect();
            }
            catch (Exception e)
            {
                Log("[DebugWS] Connect failed: " + e.Message, "red");
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
            Log("[DebugWS] Reconnect loop started.", "yellow");

            while (!_manualDisconnectRequested && !_isQuitting && !IsConnected)
            {
                Log($"[DebugWS] Reconnecting in {reconnectIntervalSeconds:F1}s...", "yellow");
                await Task.Delay(TimeSpan.FromSeconds(reconnectIntervalSeconds));

                if (_manualDisconnectRequested || _isQuitting || IsConnected) break;

                await ConnectInternal();
            }

            _isReconnecting = false;
        }

        private static void Log(string msg, string color = "white")
        {
            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.Log(msg, true, color);
            }
            else
            {
                Debug.Log(msg);
            }
        }
    }
}
