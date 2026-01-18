using UnityEngine;
using TMPro;
using System.Text;
using System.Collections.Generic;

public class SpatialDebugLog : MonoBehaviour
{
    public static SpatialDebugLog Instance { get; private set; }

    [Header("UI Reference")]
    [SerializeField] private TextMeshProUGUI logText; // Canvas上のText
    [SerializeField] private int maxLines = 15;       // 表示する最大行数

    [Header("Logging")] 
    [SerializeField] private bool globalLogEnabled = true; // 全体の出力ON/OFF

    private Queue<string> logQueue = new Queue<string>();
    private StringBuilder sb = new StringBuilder();
    

    private void Awake()
    {
        // Singletonのセットアップ
        if (Instance == null)
        {
            Instance = this;
            // シーン遷移しても残したい場合は以下を有効化
            // DontDestroyOnLoad(gameObject); 
        }
        else
        {
            Destroy(gameObject);
        }
    }

    /// <summary>
    /// 外部からこれを呼ぶだけで画面に表示される
    /// </summary>
    public void SetLogFlag(bool enabled)
    {
        globalLogEnabled = enabled;
    }

    public void Log(string message, bool doLog = true,string color = "white")
    {
        // UnityエディタのPlayモードでは、Debug.Logのみを使用（UIに依存しない）
        if (Application.isEditor)
        {
            if (globalLogEnabled && doLog)
            {
                Debug.Log($"<color={color}>[{System.DateTime.Now:HH:mm:ss}] {message}</color>");
            }
            return;
        }

        // ビルド版では通常のUI表示も行う
        Debug.Log($"<color={color}>{message}</color>");
        if(!globalLogEnabled || !doLog) return;
        
        // タイムスタンプ付与
        string formattedMsg = $"<color={color}>[{System.DateTime.Now:HH:mm:ss}] {message}</color>";

        logQueue.Enqueue(formattedMsg);

        // 行数制限を超えたら古いものを捨てる
        if (logQueue.Count > maxLines)
        {
            logQueue.Dequeue();
        }

        UpdateText();
    }

    // エラー用ショートカット
    public void LogError(string message,bool doLog=true) => Log(message, doLog, "red");
    public void LogSuccess(string message,bool doLog=true) => Log(message, doLog, "green");

    private void UpdateText()
    {
        if (logText == null) return;

        sb.Clear();
        foreach (string line in logQueue)
        {
            sb.AppendLine(line);
        }
        logText.text = sb.ToString();
    }
}