using System.Collections.Generic;
using SA_XARM.Network.Websocket;
using SA_XARM.SpatialRef.Data;
using SA_XARM.SpatialRef.Spatial;
using SA_XARM.SpatialRef.State;
using SA_XARM.SpeechRecognizer;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// HMD 上のメイン UI パネルを管理するシングルトン。
/// 4 つの TextMeshProUGUI で役割ごとに表示を分離する。
///   - UserSpeech   : ユーザーが喋った認識テキスト
///   - AgentMessage  : LLM Agent の応答（選択理由など）
///   - SystemStatus  : 処理ステージ表示 (Processing..., Found it! 等)
///   - UserPrompt    : ユーザーへの誘導 (Is "obj_15" correct? 等)
/// </summary>
public class SpeechRecognitionUIManager : MonoBehaviour
{
    public static SpeechRecognitionUIManager Instance { get; private set; }

    [Header("Core References")]
    [SerializeField] private AppStateManager appStateManager;
    [SerializeField] private SpeechRecognitionManager speechRecognitionManager;
    [SerializeField] private WebSocketManager webSocketManager;
    [SerializeField] private ObjectRegistry objectRegistry;

    [Header("Display Texts")]
    [SerializeField] private TextMeshProUGUI userSpeechText;
    [SerializeField] private TextMeshProUGUI agentMessageText;
    [SerializeField] private TextMeshProUGUI systemStatusText;
    [SerializeField] private TextMeshProUGUI userPromptText;

    [Header("Send Button")]
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
        if (Instance == null)
        {
            Instance = this;
        }
        else
        {
            Destroy(gameObject);
            return;
        }

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
    }

    private void OnDisable()
    {
        UnsubscribeSpeechEvents();
        UnsubscribeAppStateEvents();
    }

    private void OnDestroy()
    {
        if (Instance == this) Instance = null;
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

    // ───────────────────────── Public Display API ─────────────────────────

    /// <summary>ユーザーの発話テキストを表示</summary>
    public void ShowUserSpeech(string text)
    {
        SetText(userSpeechText, text);
    }

    /// <summary>LLM Agent の応答を表示（選択理由等）</summary>
    public void ShowAgentMessage(string message)
    {
        SetText(agentMessageText, message);
    }

    /// <summary>システム処理状況を表示（Processing..., Found it! 等）</summary>
    public void ShowSystemStatus(string message)
    {
        SetText(systemStatusText, message);
    }

    /// <summary>ユーザーへの誘導を表示（確認プロンプト等）</summary>
    public void ShowUserPrompt(string message)
    {
        SetText(userPromptText, message);
    }

    /// <summary>エラーメッセージをシステムステータスに表示</summary>
    public void ShowError(string message)
    {
        SetText(systemStatusText, message);
    }

    /// <summary>全テキストをクリア</summary>
    public void ClearAll()
    {
        ClearText(userSpeechText);
        ClearText(agentMessageText);
        ClearText(systemStatusText);
        ClearText(userPromptText);
    }

    /// <summary>Agent + Prompt をクリア（新しいリクエスト開始時）</summary>
    public void ClearResultTexts()
    {
        ClearText(agentMessageText);
        ClearText(userPromptText);
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

    // ───────────────────────── Event Handlers ─────────────────────────

    private void HandleSpeechStartListening()
    {
        ShowSystemStatus("Listening...");
        SetSendButtonVisible(false);
        PlaySound(onSound);
    }

    private void HandleSpeechStopListening()
    {
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
            ShowUserSpeech(text);
        }

        SetSendButtonVisible(hasPending);
    }

    private void HandleStatusChanged(string status)
    {
        if (!string.IsNullOrWhiteSpace(status))
        {
            ShowSystemStatus(status);
        }
    }

    // ───────────────────────── UI State Refresh ─────────────────────────

    private void RefreshUiFromCurrentState()
    {
        if (appStateManager == null) return;
        RefreshUiFromState(appStateManager.CurrentState);
    }

    private void RefreshUiFromState(AppState state)
    {
        bool canSend = state == AppState.Idle || state == AppState.Refining || state == AppState.ShowingResult;

        switch (state)
        {
            case AppState.Idle:
                SetSendButtonVisible(false);
                return;

            case AppState.Processing:
                SetSendButtonVisible(false);
                return;

            case AppState.Executing:
                SetSendButtonVisible(false);
                return;

            case AppState.Error:
                SetSendButtonVisible(HasUserSpeech());
                return;

            default:
                SetSendButtonVisible(canSend && HasUserSpeech());
                return;
        }
    }

    // ───────────────────────── Send Logic ─────────────────────────

    public void SendUtteredCommand()
    {
        SetSendButtonVisible(false);

        if (appStateManager == null)
        {
            ShowError("AppStateManager is not set");
            return;
        }

        if (webSocketManager != null && !webSocketManager.IsConnected)
        {
            ShowError("Server not connected");
            return;
        }

        bool sent = appStateManager.SendPendingRecognizedSpeech();
        if (sent)
        {
            ShowSystemStatus("Sent");
            return;
        }

        if (objectRegistry != null)
        {
            List<ObjectData> objects = objectRegistry.GetAll();
            if (objects.Count == 0)
            {
                ShowError("No spatial objects found");
                return;
            }
        }

        ShowError("Failed to send");
    }

    // ───────────────────────── UI Helpers ─────────────────────────

    private bool HasUserSpeech()
    {
        return userSpeechText != null && !string.IsNullOrWhiteSpace(userSpeechText.text);
    }

    private void SetSendButtonVisible(bool visible)
    {
        if (sendButton != null)
            sendButton.SetActive(visible);
    }

    private static void SetText(TextMeshProUGUI target, string message)
    {
        if (target == null) return;

        target.text = $"{message}";
        RebuildLayout(target);
    }

    private static void ClearText(TextMeshProUGUI target)
    {
        if (target == null) return;

        target.text = string.Empty;
        RebuildLayout(target);
    }

    private static void RebuildLayout(TextMeshProUGUI target)
    {
        LayoutRebuilder.ForceRebuildLayoutImmediate(target.rectTransform);

        if (target.rectTransform.parent is RectTransform parentTransform)
        {
            LayoutRebuilder.ForceRebuildLayoutImmediate(parentTransform);
        }
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
