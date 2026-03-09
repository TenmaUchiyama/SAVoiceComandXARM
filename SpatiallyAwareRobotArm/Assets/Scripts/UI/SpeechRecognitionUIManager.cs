using System.Collections.Generic;
using SA_XARM.Network.Websocket;
using SA_XARM.Network.Request;
using SA_XARM.SpatialRef.Spatial;
using SA_XARM.SpatialRef.State;
using SA_XARM.SpeechRecognizer;
using TMPro;
using UnityEngine;

public class SpeechRecognitionUIManager : MonoBehaviour
{
    [SerializeField] private SpeechRecognitionManager speechRecognitionManager;
    [SerializeField] private CommandClient commandClient;
    [SerializeField] private AppStateManager appStateManager;
    [SerializeField] private WebSocketManager webSocketManager;
    [SerializeField] private ObjectRegistry objectRegistry;
    [SerializeField] private GameObject dialogUI;
    [SerializeField] private GameObject voiceRecognionUI;
    [SerializeField] private GameObject recordingIcon;
    [SerializeField] private TextMeshProUGUI recordedText;
    [SerializeField] private GameObject sendButton;

    [Header("Audio")]
    private AudioSource audioSource;
    [SerializeField] private AudioClip onSound;
    [SerializeField] private AudioClip offSound;

    private bool appStateSubscribed;

    // Start is called before the first frame update
    void Start()
    {
        ResolveReferences();
        audioSource = GetComponent<AudioSource>();

        if (SpatialDebugLog.Instance != null)
        {
            SpatialDebugLog.Instance.Log("[SpeechRecognitionUIManager] Start");
        }

        if (speechRecognitionManager == null) return;

        speechRecognitionManager._onStartListening.AddListener(() =>
        {
            if (dialogUI != null) dialogUI.SetActive(true);
            SetRecordedText("Listening...");
            ToggleRecordingIconVisibility(true);
            PlaySound(onSound);
        });

        speechRecognitionManager._onStopListening.AddListener(() =>
        {
            ToggleRecordingIconVisibility(false);
            PlaySound(offSound);
        });


        speechRecognitionManager._onSpeechRecognized.AddListener((text) =>
        {
            if (appStateManager != null)
            {
                return;
            }

            SetRecordedText(text);
            ToggleRecordingIconVisibility(false);
            if (sendButton != null) sendButton.SetActive(true);
        });

        SubscribeAppStateEvents();
        if (sendButton != null) sendButton.SetActive(false);
    }

    private void OnDestroy()
    {
        UnsubscribeAppStateEvents();
    }

    private void ResolveReferences()
    {
        if (appStateManager == null)
        {
            appStateManager = FindObjectOfType<AppStateManager>();
        }

        if (webSocketManager == null)
        {
            webSocketManager = FindObjectOfType<WebSocketManager>();
        }

        if (objectRegistry == null)
        {
            objectRegistry = FindObjectOfType<ObjectRegistry>();
        }
    }

    private void SubscribeAppStateEvents()
    {
        if (appStateManager == null || appStateSubscribed) return;

        appStateManager.OnPendingSpeechChanged += HandlePendingSpeechChanged;
        appStateManager.OnStatusChanged += HandleStatusChanged;
        appStateSubscribed = true;
    }

    private void UnsubscribeAppStateEvents()
    {
        if (appStateManager == null || !appStateSubscribed) return;

        appStateManager.OnPendingSpeechChanged -= HandlePendingSpeechChanged;
        appStateManager.OnStatusChanged -= HandleStatusChanged;
        appStateSubscribed = false;
    }

    private void HandlePendingSpeechChanged(bool hasPending, string text, bool isFeedback)
    {
        if (hasPending)
        {
            if (dialogUI != null) dialogUI.SetActive(true);
            string label = isFeedback ? $"Feedback: {text}" : text;
            SetRecordedText(label);
        }

        if (sendButton != null)
        {
            sendButton.SetActive(hasPending);
        }
    }

    private void HandleStatusChanged(string status)
    {
        if (!string.IsNullOrWhiteSpace(status))
        {
            SetRecordedText(status);
        }
    }


    public void SendUtteredCommand()
    {
        if (sendButton != null) sendButton.SetActive(false);

        if (appStateManager != null)
        {
            if (webSocketManager != null && !webSocketManager.IsConnected)
            {
                SetRecordedText("サーバー未接続です");
                return;
            }

            bool sent = appStateManager.SendPendingRecognizedSpeech();
            if (sent)
            {
                SetRecordedText("送信しました");
            }
            else if (objectRegistry != null)
            {
                List<SA_XARM.SpatialRef.Data.ObjectData> objects = objectRegistry.GetAll();
                if (objects.Count == 0)
                {
                    SetRecordedText("空間オブジェクトが0件です（ObjectRegistry / SpatialObjects を確認）");
                }
            }

            return;
        }

        if (commandClient != null && recordedText != null)
        {
            string text = speechRecognitionManager != null
                ? speechRecognitionManager.GetRecognizedText()
                : string.Empty;

            if (string.IsNullOrWhiteSpace(text))
            {
                SetRecordedText("送信する音声テキストがありません");
                return;
            }

            commandClient.SendCommand(text);
            SetRecordedText("Command sent: " + text);
        }
    }



    public void ToggleToWake()
    {
        Debug.Log("Toggle to Wake UI");
    }


    public void ToggleToSpeech()
    {
        Debug.Log("Toggle to Speech UI");
    }



    public void SendCalibration()
    {
        _ =  XarmAppServerQueryRequester.Instance.SendCalibrationRequest();
    }



    public void SetRecordedText(string text)
    {
        if (recordedText != null)
        {
            recordedText.text = text;
        }
    }   


    public void ToggleRecordingIconVisibility(bool isVisible)
    {
        if (recordingIcon != null)
        {
            recordingIcon.SetActive(isVisible);
        }
    }

    private void PlaySound(AudioClip clip)
    {
        if (audioSource != null && clip != null)
        {
            audioSource.PlayOneShot(clip);
        }
    }
    
}
