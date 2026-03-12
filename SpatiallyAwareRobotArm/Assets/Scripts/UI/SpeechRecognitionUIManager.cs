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
/// SpeechRecognitionManager と WakeWordManager で認識を行い、
/// AppStateManager 経由で WebSocket サーバーへリクエストを送信する。
/// </summary>
public class SpeechRecognitionUIManager : MonoBehaviour
{
    [Header("Core References")]
    [SerializeField] private AppStateManager appStateManager;
    [SerializeField] private SpeechRecognitionManager speechRecognitionManager;
    [SerializeField] private WebSocketManager webSocketManager;
    [SerializeField] private ObjectRegistry objectRegistry;

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
    }

    private void OnDestroy()
    {
        UnsubscribeSpeechEvents();
        UnsubscribeAppStateEvents();
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

    // ───────────────────────── Speech Event Handlers ─────────────────────────

    private void HandleSpeechStartListening()
    {
        SetDialogVisible(true);
        SetVoiceRecognitionVisible(true);
        SetRecordedText("Listening...");
        ToggleRecordingIconVisibility(true);
        SetSendButtonVisible(false);
        PlaySound(onSound);
    }

    private void HandleSpeechStopListening()
    {
        ToggleRecordingIconVisibility(false);
        PlaySound(offSound);
        RefreshUiFromCurrentState();
    }

    // ───────────────────────── AppState Event Handlers ─────────────────────────

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
            string label = isFeedback ? $"確認: {text}" : text;
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
        bool isListening = state == AppState.Listening;
        bool canSend = state == AppState.Idle || state == AppState.Refining || state == AppState.ShowingResult;
        bool showDialog = state != AppState.Idle || HasRecognizedText();

        SetDialogVisible(showDialog);
        SetVoiceRecognitionVisible(true);
        ToggleRecordingIconVisibility(isListening);

        switch (state)
        {
            case AppState.Processing:
                SetSendButtonVisible(false);
                SetRecordedText("推論中...");
                return;

            case AppState.Executing:
                SetSendButtonVisible(false);
                return;

            case AppState.Error:
                SetSendButtonVisible(CanSend());
                return;

            default:
                SetSendButtonVisible(canSend && CanSend());
                return;
        }
    }

    // ───────────────────────── Send Logic ─────────────────────────

    /// <summary>
    /// UI の送信ボタンから呼ばれる。
    /// AppStateManager に溜まっている認識テキストをサーバーへ送信する。
    /// </summary>
    public void SendUtteredCommand()
    {
        SetSendButtonVisible(false);

        if (appStateManager == null)
        {
            SetRecordedText("AppStateManager が未設定です");
            return;
        }

        if (webSocketManager != null && !webSocketManager.IsConnected)
        {
            SetRecordedText("サーバー未接続です");
            return;
        }

        bool sent = appStateManager.SendPendingRecognizedSpeech();
        if (sent)
        {
            SetRecordedText("送信しました");
            return;
        }

        // 送信失敗の理由を表示
        if (objectRegistry != null)
        {
            List<ObjectData> objects = objectRegistry.GetAll();
            if (objects.Count == 0)
            {
                SetRecordedText("空間オブジェクトが0件です（ObjectRegistry / SpatialObjects を確認）");
                return;
            }
        }

        SetRecordedText("送信できませんでした");
    }

    // ───────────────────────── Wake / Speech Toggle ─────────────────────────

    /// <summary>
    /// WakeWord 待機モードへ切り替える（音声認識 UI を非表示にする）。
    /// </summary>
    public void ToggleToWake()
    {
        SetVoiceRecognitionVisible(false);
        SetDialogVisible(false);
        SetSendButtonVisible(false);
        ToggleRecordingIconVisibility(false);
    }

    /// <summary>
    /// 音声認識モードへ切り替える（UI を表示して状態を反映する）。
    /// </summary>
    public void ToggleToSpeech()
    {
        SetVoiceRecognitionVisible(true);
        RefreshUiFromCurrentState();
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
