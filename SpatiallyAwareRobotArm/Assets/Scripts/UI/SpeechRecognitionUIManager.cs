using System.Collections.Generic;
using SA_XARM.Network.Request;
using SA_XARM.Network.Websocket;
using SA_XARM.SpatialRef.Data;
using SA_XARM.SpatialRef.Spatial;
using SA_XARM.SpatialRef.State;
using SA_XARM.SpeechRecognizer;
using TMPro;
using UnityEngine;

/// <summary>
/// 音声認識関連の UI を管理する。
/// AppStateManager のイベントを購読し、状態に応じて Dialog / 録音アイコン / 送信ボタンを切り替える。
/// SpeechRecognitionManager で認識を行い、
/// AppStateManager 経由で WebSocket サーバーへリクエストを送信する。
/// </summary>
public class SpeechRecognitionUIManager : MonoBehaviour
{
    [Header("Core References")]
    [SerializeField] private AppStateManager appStateManager;
    [SerializeField] private SpeechRecognitionManager speechRecognitionManager;
    [SerializeField] private WebSocketManager webSocketManager;
    [SerializeField] private ObjectRegistry objectRegistry;
    [SerializeField] private LanguageSettings languageSettings;

    [Header("UI Elements")]
    [SerializeField] private GameObject dialogUI;
    [SerializeField] private GameObject voiceRecognitionUI;
    [SerializeField] private GameObject recordingIcon;
    [SerializeField] private TextMeshProUGUI recordedText;
    [SerializeField] private GameObject sendButton;

    [Header("Audio")]
    [SerializeField] private AudioClip onSound;
    [SerializeField] private AudioClip offSound;

    private AudioSource audioSource;
    private bool appStateSubscribed;
    private bool speechEventsSubscribed;
    private bool languageEventsSubscribed;

    // ───────────────────────── Lifecycle ─────────────────────────

    private void Awake()
    {
        ResolveReferences();
        audioSource = GetComponent<AudioSource>();
    }

    private void OnEnable()
    {
        ResolveReferences();
        SubscribeSpeechEvents();
        SubscribeAppStateEvents();
        SubscribeLanguageEvents();
        RefreshUiFromCurrentState();
    }

    private void Start()
    {
        RefreshUiFromCurrentState();
        Log("[SpeechRecognitionUIManager] Start");
    }

    private void OnDisable()
    {
        UnsubscribeSpeechEvents();
        UnsubscribeAppStateEvents();
        UnsubscribeLanguageEvents();
    }

    private void OnDestroy()
    {
        UnsubscribeSpeechEvents();
        UnsubscribeAppStateEvents();
        UnsubscribeLanguageEvents();
    }

    // ───────────────────────── Reference Resolution ─────────────────────────

    private void ResolveReferences()
    {
        if (appStateManager == null)
            appStateManager = FindObjectOfType<AppStateManager>();

        if (speechRecognitionManager == null)
            speechRecognitionManager = FindObjectOfType<SpeechRecognitionManager>();

        if (webSocketManager == null)
            webSocketManager = WebSocketManager.Instance;

        if (objectRegistry == null)
            objectRegistry = FindObjectOfType<ObjectRegistry>();

        if (languageSettings == null)
            languageSettings = LanguageSettings.Instance;

        if (languageSettings == null)
            languageSettings = FindObjectOfType<LanguageSettings>();
    }

    public void ToggleVoiceRecognitionUI()
    {
        Debug.Log("ToggleVoiceRecognitionUI called");
        if (voiceRecognitionUI != null)
        {
            bool visible = !voiceRecognitionUI.activeSelf;
            voiceRecognitionUI.SetActive(visible);
        }
    }

    // ───────────────────────── Event Subscription ─────────────────────────

    private void SubscribeSpeechEvents()
    {
        if (speechRecognitionManager == null || speechEventsSubscribed) return;

        speechRecognitionManager._onStartListening.AddListener(HandleSpeechStartListening);
        speechRecognitionManager._onStopListening.AddListener(HandleSpeechStopListening);
        speechEventsSubscribed = true;
    }

    private void UnsubscribeSpeechEvents()
    {
        if (speechRecognitionManager == null || !speechEventsSubscribed) return;

        speechRecognitionManager._onStartListening.RemoveListener(HandleSpeechStartListening);
        speechRecognitionManager._onStopListening.RemoveListener(HandleSpeechStopListening);
        speechEventsSubscribed = false;
    }

    private void SubscribeAppStateEvents()
    {
        if (appStateManager == null || appStateSubscribed) return;

        appStateManager.OnStateChanged += HandleStateChanged;
        appStateManager.OnPendingSpeechChanged += HandlePendingSpeechChanged;
        appStateManager.OnStatusChanged += HandleStatusChanged;
        appStateSubscribed = true;
    }

    private void UnsubscribeAppStateEvents()
    {
        if (appStateManager == null || !appStateSubscribed) return;

        appStateManager.OnStateChanged -= HandleStateChanged;
        appStateManager.OnPendingSpeechChanged -= HandlePendingSpeechChanged;
        appStateManager.OnStatusChanged -= HandleStatusChanged;
        appStateSubscribed = false;
    }

    private void SubscribeLanguageEvents()
    {
        if (languageSettings == null || languageEventsSubscribed) return;

        languageSettings.OnLanguageChanged += HandleLanguageChanged;
        languageEventsSubscribed = true;
    }

    private void UnsubscribeLanguageEvents()
    {
        if (languageSettings == null || !languageEventsSubscribed) return;

        languageSettings.OnLanguageChanged -= HandleLanguageChanged;
        languageEventsSubscribed = false;
    }

    // ───────────────────────── Event Handlers ─────────────────────────

    private void HandleLanguageChanged(string lang)
    {
        RefreshUiFromCurrentState();
    }

    private void HandleSpeechStartListening()
    {
        SetDialogVisible(true);
        SetVoiceRecognitionVisible(true);
        SetRecordedText(GetText("listening"));
        ToggleRecordingIconVisibility(true);
        SetSendButtonVisible(false);
        PlaySound(onSound);
    }

    private void HandleSpeechStopListening()
    {
        // 常時収音モードのため録音アイコンは維持
        PlaySound(offSound);
        RefreshUiFromCurrentState();
    }

    private void HandleStateChanged(AppState state)
    {
        RefreshUiFromState(state);
    }

    private void HandlePendingSpeechChanged(bool hasPending, string text, bool isFeedback)
    {
        if (hasPending)
        {
            SetDialogVisible(true);
            SetVoiceRecognitionVisible(true);
            string label = isFeedback ? GetText("confirm", text) : text;
            SetRecordedText(label);
        }

        SetSendButtonVisible(hasPending);
    }

    private void HandleStatusChanged(string status)
    {
        if (!string.IsNullOrWhiteSpace(status))
        {
            SetRecordedText(status);
        }
    }

    // ───────────────────────── UI State Refresh ─────────────────────────

    private void RefreshUiFromCurrentState()
    {
        if (appStateManager == null)
        {
            Log("[SpeechRecognitionUIManager] AppStateManager が見つかりません", "red");
            return;
        }

        RefreshUiFromState(appStateManager.CurrentState);
    }

    private void RefreshUiFromState(AppState state)
    {
        bool canSend = state == AppState.Idle || state == AppState.Refining || state == AppState.ShowingResult;
        bool showDialog = state != AppState.Idle || HasRecognizedText();
        // 常時収音モード: SpeechRecognitionManager が動いていれば常にアイコンを表示
        bool mic = speechRecognitionManager != null && speechRecognitionManager.IsListening;

        SetDialogVisible(showDialog);
        SetVoiceRecognitionVisible(true);
        ToggleRecordingIconVisibility(mic);

        switch (state)
        {
            case AppState.Processing:
                SetSendButtonVisible(false);
                SetRecordedText(GetText("processing"));
                return;

            case AppState.Executing:
                SetSendButtonVisible(false);
                return;

            case AppState.Error:
                SetSendButtonVisible(HasRecognizedText());
                return;

            default:
                SetSendButtonVisible(canSend && HasRecognizedText());
                return;
        }
    }

    // ───────────────────────── Send Logic ─────────────────────────

    public void SendUtteredCommand()
    {
        SetSendButtonVisible(false);

        if (appStateManager == null)
        {
            SetRecordedText(GetText("app_state_not_set"));
            return;
        }

        if (webSocketManager != null && !webSocketManager.IsConnected)
        {
            SetRecordedText(GetText("server_not_connected"));
            return;
        }

        bool sent = appStateManager.SendPendingRecognizedSpeech();
        if (sent)
        {
            SetRecordedText(GetText("sent"));
            return;
        }

        // 送信失敗の理由を表示
        if (objectRegistry != null)
        {
            List<ObjectData> objects = objectRegistry.GetAll();
            if (objects.Count == 0)
            {
                SetRecordedText(GetText("no_objects"));
                return;
            }
        }

        SetRecordedText(GetText("failed_to_send"));
    }

    // ───────────────────────── Localization ─────────────────────────

    private string GetText(string key, string arg0 = null)
    {
        string lang = languageSettings != null ? languageSettings.CurrentLanguage : "ja";
        bool isJa = lang == "ja";

        switch (key)
        {
            case "listening": return isJa ? "収音中..." : "Listening...";
            case "processing": return isJa ? "推論中..." : "Processing...";
            case "confirm": return isJa ? $"確認: {arg0}" : $"Confirm: {arg0}";
            case "app_state_not_set": return isJa ? "AppStateManager が未設定です" : "AppStateManager is not set";
            case "server_not_connected": return isJa ? "サーバー未接続です" : "Server not connected";
            case "sent": return isJa ? "送信しました" : "Sent";
            case "no_objects": return isJa ? "空間オブジェクトが0件です" : "No spatial objects found";
            case "failed_to_send": return isJa ? "送信できませんでした" : "Failed to send";
            default: return key;
        }
    }

    // ───────────────────────── Calibration ─────────────────────────

    public void SendCalibration()
    {
        _ = XarmAppServerQueryRequester.Instance.SendCalibrationRequest();
    }

    // ───────────────────────── UI Helpers ─────────────────────────

    private bool HasRecognizedText()
    {
        return recordedText != null && !string.IsNullOrWhiteSpace(recordedText.text);
    }

    private bool CanSend()
    {
        if (webSocketManager != null && !webSocketManager.IsConnected)
            return false;

        if (objectRegistry != null && objectRegistry.GetAll().Count == 0)
            return false;

        return true;
    }

    private void SetDialogVisible(bool visible)
    {
        if (dialogUI != null)
            dialogUI.SetActive(visible);
    }

    private void SetVoiceRecognitionVisible(bool visible)
    {
        if (voiceRecognitionUI != null)
            voiceRecognitionUI.SetActive(visible);
    }

    private void SetSendButtonVisible(bool visible)
    {
        if (sendButton != null)
            sendButton.SetActive(visible);
    }

    public void SetRecordedText(string text)
    {
        if (recordedText != null)
            recordedText.text = text;
    }

    public void ToggleRecordingIconVisibility(bool isVisible)
    {
        if (recordingIcon != null)
            recordingIcon.SetActive(isVisible);
    }

    private void PlaySound(AudioClip clip)
    {
        if (audioSource != null && clip != null)
            audioSource.PlayOneShot(clip);
    }

    // ───────────────────────── Logging ─────────────────────────

    private void Log(string message, string color = "white")
    {
        if (SpatialDebugLog.Instance != null)
            SpatialDebugLog.Instance.Log(message, true, color);
        else
            Debug.Log(message);
    }
}
