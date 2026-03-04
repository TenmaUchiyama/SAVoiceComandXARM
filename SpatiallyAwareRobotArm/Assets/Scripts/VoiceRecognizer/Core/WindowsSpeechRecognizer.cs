using UnityEngine.Windows.Speech;
using System; 

namespace SA_XARM.SpeechRecognizer
{
    public class WindowsSpeechRecognizer : ISpeechRecognizer
    {
        public event Action<string> OnRecognized;
        public event Action<string> OnError;
        public event Action OnSilenceTimeout;

        private DictationRecognizer recognizer;

        /// <summary>
        /// 無音タイムアウト秒数（デフォルト2秒）
        /// </summary>
        public float AutoSilenceTimeout { get; set; } = 2.0f;

        /// <summary>
        /// 初期無音タイムアウト秒数（話し始めるまでの猶予、デフォルト5秒）
        /// </summary>
        public float InitialSilenceTimeout { get; set; } = 5.0f;

        public void StartListening()
        {
            recognizer = new DictationRecognizer();
            
            // 無音タイムアウトの設定
            recognizer.AutoSilenceTimeoutSeconds = AutoSilenceTimeout;
            recognizer.InitialSilenceTimeoutSeconds = InitialSilenceTimeout;

            recognizer.DictationResult += (text, confidence) =>
            {
                OnRecognized?.Invoke(text);
            };
            recognizer.DictationError += (error, hresult) =>
            {
                OnError?.Invoke(error);
            };
            recognizer.DictationComplete += (cause) =>
            {
                // タイムアウトで終了した場合
                if (cause == DictationCompletionCause.Complete || 
                    cause == DictationCompletionCause.TimeoutExceeded)
                {
                    OnSilenceTimeout?.Invoke();
                }
            };
            recognizer.Start();
        }

    public void StopListening()
    {
        recognizer?.Stop();
        recognizer?.Dispose();
    }
}
}