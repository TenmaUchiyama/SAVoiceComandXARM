

namespace SA_XARM.SpeechRecognizer
{
public static class SpeechRecognizerFactory
{


    public static string selectedRecognizer = "";
    public static ISpeechRecognizer Create()
    {
#if UNITY_WSA && !UNITY_EDITOR
        // HoloLens 実機ビルド
        selectedRecognizer = "WindowsSpeechRecognizer";
        return new WindowsSpeechRecognizer();
#else
        // Editor / デバッグ / Remoting
        if (UnityEngine.Application.isPlaying)
        {
            selectedRecognizer = "PlayModeMicrophoneSpeechRecognizer";
            // エディタの再生中はマイク入力を使用
            return new PlayModeMicrophoneSpeechRecognizer();
        }

        selectedRecognizer = "DebugTextSpeechRecognizer";
        // 念のためのフォールバック（非再生時）
        return new DebugTextSpeechRecognizer();
#endif
    }
}
}