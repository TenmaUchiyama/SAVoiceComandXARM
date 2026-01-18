using System;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;
using UnityEngine.Windows.Speech;

namespace SA_XARM.SpeechRecognizer
{
    public class SpeechRecognitionManager : MonoBehaviour
    {
        [SerializeField] private TextMeshProUGUI userText;
        [SerializeField] private RawImage microphoneButton;
        [SerializeField] private GameObject recordingIcon;
        
        public bool isListening { get; private set; } = false;

        public UnityEvent<string> _onSpeechRecognized;
        public UnityEvent _onStartListening;
        public UnityEvent _onStopListening;

        private ISpeechRecognizer speechRecognizer;

        void Awake()
        {
            speechRecognizer = SpeechRecognizerFactory.Create();
            speechRecognizer.OnRecognized += OnSpeechRecognized;
            speechRecognizer.OnError += OnVoiceError;

            Debug.Log("[SpeechRecognitionManager] Selected Recognizer: "
                + SpeechRecognizerFactory.selectedRecognizer);
        }

        private void OnVoiceError(string text)
        {
            Debug.LogError("[SpeechRecognitionManager] Voice Error: " + text);
        }

        private void OnSpeechRecognized(string text)
        {
            Debug.Log("[SpeechRecognitionManager] Recognized: " + text);

            if (userText != null)
            {
                userText.text = text;
            }

            // 認識完了後はボタンを半透明に戻す
            SetButtonAppearance(Color.white, 0.5f);

            _onSpeechRecognized?.Invoke(text);
        }

        public void ToggleListening()
        {
            if (isListening)
            {
                StopListening();
                recordingIcon.SetActive(false);
            }
            else
            {
                StartListening();
                recordingIcon.SetActive(true);
            }
        }

        public void StartListening()
        {
            if (isListening)
            {
                Debug.LogWarning("[SpeechRecognitionManager] Already listening");
                return;
            }

            Debug.Log("[SpeechRecognitionManager] StartListening");

            // ★ PhraseRecognitionSystem を止める
            if (PhraseRecognitionSystem.Status == SpeechSystemStatus.Running)
            {
                Debug.Log("[SpeechRecognitionManager] Shutdown PhraseRecognitionSystem");
                PhraseRecognitionSystem.Shutdown();
            }

            speechRecognizer.StartListening();
  
            isListening = true;
            
            // ボタンを完全に不透明の緑色に変更
            SetButtonAppearance(Color.green, 1.0f);
            
            _onStartListening?.Invoke();

        }

        public void StopListening()
        {
            if (!isListening)
            {
                Debug.LogWarning("[SpeechRecognitionManager] Not listening");
                return;
            }

            Debug.Log("[SpeechRecognitionManager] StopListening");

            speechRecognizer.StopListening();

            // ★ WakeWord を復活させる
            if (PhraseRecognitionSystem.Status == SpeechSystemStatus.Stopped)
            {
                Debug.Log("[SpeechRecognitionManager] Restart PhraseRecognitionSystem");
                PhraseRecognitionSystem.Restart();
            }

            isListening = false;
            
            // ボタンを半透明の白色に変更
            SetButtonAppearance(Color.white, 0.5f);
            
            _onStopListening?.Invoke();
        }

        /// <summary>
        /// ボタンの色と透明度を設定します
        /// </summary>
        private void SetButtonAppearance(Color color, float alpha)
        {
            if (microphoneButton != null)
            {
                Color buttonColor = color;
                buttonColor.a = alpha;
                microphoneButton.color = buttonColor;
            }
        }
    }
}
