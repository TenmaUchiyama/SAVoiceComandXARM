using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class TestLog : MonoBehaviour
{
    private int testLogCounter = 0;
    void Start()
    {
        
        InvokeRepeating(nameof(LogTestMessage), 0f, 1f); // 毎秒テストログを出力
    }

    /// <summary>
    /// テスト用：毎秒ログを出力
    /// </summary>
    private void LogTestMessage()
    {


        testLogCounter++;
        string[] colors = { "white", "yellow", "cyan", "magenta", "lime", "orange" };
        string color = colors[testLogCounter % colors.Length];
        Debug.Log(color);
        SpatialDebugLog.Instance.Log($"テストログ #{testLogCounter}");
    }
}
