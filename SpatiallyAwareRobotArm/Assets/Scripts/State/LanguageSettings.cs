using System;
using Newtonsoft.Json;
using SA_XARM.Network.Websocket;
using SA_XARM.SpeechRecognizer;
using SA_XARM.WakeWord;
using UnityEngine;

namespace SA_XARM.SpatialRef.State
{
    [Serializable]
    public class SetLanguageMessage
    {
        public string type;
        public string language;
    }

    /// <summary>
    /// フロントアプリから set_language メッセージを受信し、
    /// AppStateManager の言語設定と WakeWord を切り替える。
    /// DebugWebSocketClient (port 8765) を経由して受信する。
    /// </summary>
    public class LanguageSettings : MonoBehaviour
    {
        public static LanguageSettings Instance { get; private set; }

        [Header("References")]
        [SerializeField] private AppStateManager appStateManager;
        [SerializeField] private WakeWordManager wakeWordManager;

        [Header("Current Language")]
        [SerializeField] private string currentLanguage = "ja";
        [SerializeField] private bool autoDetectSystemLanguage = true;

        public string CurrentLanguage => currentLanguage;

        public event Action<string> OnLanguageChanged;

        private DebugWebSocketClient _debugClient;

        private void Awake()
        {
            if (Instance == null)
                Instance = this;
            else
                Destroy(this);

            // if (autoDetectSystemLanguage)
            // {
            //     currentLanguage = Application.systemLanguage == SystemLanguage.Japanese ? "ja" : "en";
            //     Debug.Log($"[LanguageSettings] System language detected: {Application.systemLanguage} → {currentLanguage}");
            // }
        }

        private void Start()
        {
            _debugClient = DebugWebSocketClient.Instance;
            if (_debugClient != null)
            {
                _debugClient.On<SetLanguageMessage>("set_language", OnSetLanguageReceived);
                Debug.Log("[LanguageSettings] Subscribed to set_language event");
            }
            else
            {
                Debug.LogWarning("[LanguageSettings] DebugWebSocketClient not found, retrying in Update");
            }
        }

        private void Update()
        {
            // Lazy subscribe if DebugWebSocketClient wasn't ready at Start
            if (_debugClient == null)
            {
                _debugClient = DebugWebSocketClient.Instance;
                if (_debugClient != null)
                {
                    _debugClient.On<SetLanguageMessage>("set_language", OnSetLanguageReceived);
                    Debug.Log("[LanguageSettings] Late-subscribed to set_language event");
                }
            }
        }

        private void OnDestroy()
        {
            if (Instance == this) Instance = null;
            _debugClient?.Off("set_language");
        }

        private void OnSetLanguageReceived(SetLanguageMessage msg)
        {
            if (msg == null || string.IsNullOrWhiteSpace(msg.language)) return;

            string newLang = msg.language.Trim().ToLowerInvariant();
            if (newLang == currentLanguage) return;

            string oldLang = currentLanguage;
            currentLanguage = newLang;

            Debug.Log($"[LanguageSettings] Language changed: {oldLang} -> {newLang}");

            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.Log(
                    $"[LanguageSettings] Language: {newLang}", true, "cyan");
            }

            OnLanguageChanged?.Invoke(newLang);
        }

        /// <summary>
        /// コードから直接言語を変更する場合
        /// </summary>
        public void SetLanguage(string language)
        {
            OnSetLanguageReceived(new SetLanguageMessage { language = language });
        }
    }
}
