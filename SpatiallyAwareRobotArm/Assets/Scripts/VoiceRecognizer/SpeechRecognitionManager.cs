using System;
using System.Collections;
using TMPro;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.UI;

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
            speechRecognizer.OnRecognized += HandleRecognized;
            speechRecognizer.OnError += OnVoiceError;
            speechRecognizer.OnCompleted += OnRecognizerCompleted;

            SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] Selected Recognizer: "
                + SpeechRecognizerFactory.selectedRecognizer);
        }

        private void HandleRecognized(string text)
        {
            LastRecognizedText = text;
            SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] Recognized: " + text);
            if (userText != null) userText.text = text;
            _onSpeechRecognized?.Invoke(text);
            OnSpeechRecognized?.Invoke(text);
        }

        private void OnVoiceError(string text)
        {
            SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] Voice Error: " + text);
        }

        private void OnRecognizerCompleted()
        {
            // DictationRecognizer がタイムアウト等で終了したら次フレームで再起動
            if (isListening)
            {
                StartCoroutine(RestartListeningCoroutine());
            }
        }

        private IEnumerator RestartListeningCoroutine()
        {
            isListening = false;
            yield return null; // 1フレーム待つ
            SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] Restarting DictationRecognizer...");
            speechRecognizer.StartListening();
            isListening = true;
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

        private void Start()
        {
            StartListening();
        }

        public void StartListening()
        {
            if (isListening)
            {
                SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] Already listening");
                return;
            }

            SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] StartListening");

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
                SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] Not listening");
                return;
            }

            SpatialDebugLog.Instance?.Log("[SpeechRecognitionManager] StopListening");

            speechRecognizer.StopListening();

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
