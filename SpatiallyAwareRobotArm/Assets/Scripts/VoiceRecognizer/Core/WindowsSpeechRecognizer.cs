using UnityEngine.Windows.Speech;
using System;

namespace SA_XARM.SpeechRecognizer
{
    public class WindowsSpeechRecognizer : ISpeechRecognizer
    {
        public event Action<string> OnRecognized;
        public event Action<string> OnError;
        public event Action OnCompleted;

        private DictationRecognizer recognizer;
        private bool _shouldBeListening = false;

        public void StartListening()
        {
            _shouldBeListening = true;
            recognizer?.Dispose();
            recognizer = new DictationRecognizer();

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
                // タイムアウト等でセッションが終了したら上位に通知し、再起動を委譲
                if (_shouldBeListening)
                {
                    OnCompleted?.Invoke();
                }
            };

            recognizer.Start();
        }

        public void StopListening()
        {
            _shouldBeListening = false;
            recognizer?.Stop();
            recognizer?.Dispose();
            recognizer = null;
        }
    }
}