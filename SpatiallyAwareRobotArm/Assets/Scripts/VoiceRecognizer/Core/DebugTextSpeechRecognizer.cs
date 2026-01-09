using System;
using UnityEngine;

namespace SA_XARM.SpeechRecognizer
{

    public class DebugTextSpeechRecognizer : ISpeechRecognizer
{
    public event Action<string> OnRecognized;
    public event Action<string> OnError;

    public void StartListening()
    {
        Debug.Log("[DebugVoice] StartListening");
    }

    public void StopListening()
    {
        // 何もしない
    }

    // Inspector や UI ボタンから呼ぶ
    public void InjectText(string text)
    {
        OnRecognized?.Invoke(text);
    }
}

}
