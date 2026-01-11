using System;
using System.Collections.Generic;
using UnityEngine;
using NativeWebSocket; // GitHubから導入が必要


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

    [Header("Settings")]
    [SerializeField] private string serverUrl = "ws://localhost:8080/ws";
    [SerializeField] private bool autoConnectOnStart = false; // ← 自動接続スイッチ

    private WebSocket _websocket;
    private Dictionary<string, Action<string>> _handlers = new Dictionary<string, Action<string>>();

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
    }

    private void Start()
    {
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
            if (_websocket != null && _websocket.State == WebSocketState.Open)
            {
                _websocket.DispatchMessageQueue();
            }
        #endif
    }

    private async void OnApplicationQuit()
    {
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
        // 既に接続中なら何もしない（連打防止）
        if (_websocket != null && 
           (_websocket.State == WebSocketState.Open || _websocket.State == WebSocketState.Connecting))
        {
            Debug.LogWarning("Already connected or connecting.");
            return;
        }

        Debug.Log("Connecting...");
        
        // インスタンスを生成（再接続時にも新しく作る必要がある）
        _websocket = new WebSocket(serverUrl);

        // イベント定義
        _websocket.OnOpen += () => Debug.Log("WS Connected!");
        _websocket.OnError += (e) => Debug.LogError("WS Error: " + e);
        _websocket.OnClose += (e) => Debug.Log("WS Closed: " + e);
        
        // メッセージ受信処理
        _websocket.OnMessage += (bytes) =>
        {
            var json = System.Text.Encoding.UTF8.GetString(bytes);
            try 
            {
                var packet = JsonUtility.FromJson<WSPacket>(json);
                if (_handlers.ContainsKey(packet.eventId))
                {
                    _handlers[packet.eventId]?.Invoke(packet.payload);
                }
            }
            catch (Exception e)
            {
                Debug.LogError($"Parse Error: {e.Message}");
            }
        };

        // 実際に接続
        await _websocket.Connect();
    }

    /// <summary>
    /// 切断（切断ボタン用）
    /// </summary>
    public async System.Threading.Tasks.Task Disconnect()
    {
        if (_websocket != null)
        {
            await _websocket.Close();
            _websocket = null;
            Debug.Log("Disconnected.");
        }
    }

    // ... Send, On, Off メソッドは変更なし（前のコードのまま） ...
     public void Send<T>(string eventId, T data)
    {
        if (_websocket == null || _websocket.State != WebSocketState.Open) return;
        string jsonPayload = JsonUtility.ToJson(data);
        var packet = new WSPacket { eventId = eventId, payload = jsonPayload };
        _websocket.SendText(JsonUtility.ToJson(packet));
    }

    public void On<T>(string eventId, Action<T> callback)
    {
        if (_handlers.ContainsKey(eventId)) _handlers.Remove(eventId);
        _handlers.Add(eventId, (jsonPayload) => {
            T data = JsonUtility.FromJson<T>(jsonPayload);
            callback(data);
        });
    }

    public void Off(string eventId)
    {
        if (_handlers.ContainsKey(eventId)) _handlers.Remove(eventId);
    }
}}