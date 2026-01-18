using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;



namespace SA_XARM.Network.Websocket{


[System.Serializable]
public class MyMessage
{
    public string text;
}

public class MouseKeyInput
{
    public string type;
    public string key;
}


public class TestWebsocketReceiver : MonoBehaviour
{

    [SerializeField] private TextMeshProUGUI debugText; 

   void Start()
    {
        // ▼ 受信設定：サーバーから "ServerReply" というラベルで返事が来たらログに出す
        WebSocketManager.Instance.On<MyMessage>("ServerReply", (msg) => 
        {
            Debug.Log($"サーバーからの返事: {msg.text}");
        });



    

        // ▼ 受信設定：サーバーから "Ping" が来たらログに出す
        WebSocketManager.Instance.On<MyMessage>("Ping", (msg) => 
        {
            Debug.Log($"時報: {msg.text}");
            if (debugText != null)
            {
                debugText.text = $"時報: {msg.text}";
            }
        });






        WebSocketManager.Instance.On<MouseKeyInput>("KeyInput", (input) => 
        {
            Debug.Log($"Key Input Received: type={input.type}, key={input.key}");
            SpatialDebugLog.Instance.Log($"[TestWebsocketReceiver] Key Input Received: type={input.type}, key={input.key}", true, "red");
        });
    }

    // これをボタンに割り当てるか、キーボードのAを押してテスト
    void Update()
    {
        if (Input.GetKeyDown(KeyCode.A))
        {
            SendHello();
        }
    }

    public void SendHello()
    {
        var data = new MyMessage { text = "こんにちは、サーバー！" };
        
        Debug.Log("送信: " + data.text);
        
        // "TestChat" というラベルで送信
        WebSocketManager.Instance.Send("TestChat", data);
    }
}
}