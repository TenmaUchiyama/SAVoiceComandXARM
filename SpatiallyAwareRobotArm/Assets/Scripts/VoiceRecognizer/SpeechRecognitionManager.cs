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
        public bool IsListening => isListening;

        public string LastRecognizedText { get; private set; } = string.Empty;

        public UnityEvent<string> _onSpeechRecognized = new UnityEvent<string>();
        public UnityEvent _onStartListening = new UnityEvent();
        public UnityEvent _onStopListening = new UnityEvent();

        public UnityEvent<string> OnSpeechRecognizedEvent => _onSpeechRecognized;
        public UnityEvent OnStartListeningEvent => _onStartListening;
        public UnityEvent OnStopListeningEvent => _onStopListening;

        public event Action<string> OnSpeechRecognized;
        public event Action OnStartedListening;
        public event Action OnStoppedListening;

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



        public void ToggleListening()
        {
            if (isListening)
            {
                StopListening();
                if (recordingIcon != null)
                {
                    recordingIcon.SetActive(false);
                }
            }
            else
            {
                StartListening();
                if (recordingIcon != null)
                {
                    recordingIcon.SetActive(true);
                }
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
            OnStartedListening?.Invoke();

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
            OnStoppedListening?.Invoke();
        }

        public string GetRecognizedText()
        {
            return LastRecognizedText;
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
