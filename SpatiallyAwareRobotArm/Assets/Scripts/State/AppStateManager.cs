using System;
using System.Collections;
using SA_XARM.Network.Websocket;
using SA_XARM.SpatialRef.Data;
using SA_XARM.SpatialRef.Spatial;
using SA_XARM.SpeechRecognizer;
using UnityEngine;

namespace SA_XARM.SpatialRef.State
{
    public enum AppState
    {
        Idle,
        Listening,
        Processing,
        ShowingResult,
        Refining,
        Executing,
        Error
    }

    public class AppStateManager : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private SpeechRecognitionManager speechRecognitionManager;
        [SerializeField] private SpatialContextProvider spatialContextProvider;
        [SerializeField] private WebSocketManager webSocketManager;

        [Header("Settings")]
        [SerializeField] private string language = "en";
        [SerializeField] private bool autoSubscribeOnEnable = true;

        public string Language => language;

        public AppState CurrentState { get; private set; } = AppState.Idle;

        public event Action<AppState> OnStateChanged;
        public event Action<string> OnStatusChanged;
        public event Action<SpatialReferenceResult> OnResultUpdated;
        public event Action<bool, string, bool> OnPendingSpeechChanged;

        private string _lastRequestId;
        private string _lastTargetObjectId;
        private SpatialObject _highlightedSpatialObject;
        private string _pendingRecognizedText;
        private bool _pendingIsFeedback;

        private void OnEnable()
        {
            if (!autoSubscribeOnEnable) return;
            Subscribe();
        }

        private void OnDisable()
        {
            if (!autoSubscribeOnEnable) return;
            Unsubscribe();
        }

        public void Subscribe()
        {
            if (speechRecognitionManager != null)
            {
                speechRecognitionManager._onSpeechRecognized.AddListener(HandleSpeechRecognized);
                speechRecognitionManager._onStartListening.AddListener(OnStartListening);
                speechRecognitionManager._onStopListening.AddListener(OnStopListening);
            }

            if (webSocketManager != null)
            {
                webSocketManager.On<SpatialReferenceResult>("spatial_reference_result", OnResultReceived);
                webSocketManager.On<RobotCommand>("robot_command", OnRobotCommandReceived);
                webSocketManager.On<ServerErrorMessage>("error", OnServerErrorReceived);
                webSocketManager.On<ServerErrorMessage>("server_error", OnServerErrorReceived);
                webSocketManager.On<ProcessingStatus>("processing_status", OnProcessingStatusReceived);
            }

            // LanguageSettings からの言語変更を購読
            if (LanguageSettings.Instance != null)
            {
                LanguageSettings.Instance.OnLanguageChanged += OnLanguageChanged;
            }
        }

        private void OnLanguageChanged(string newLanguage)
        {
            language = newLanguage;
            Log($"Language updated to: {newLanguage}", "cyan");
        }

        public void Unsubscribe()
        {
            if (speechRecognitionManager != null)
            {
                speechRecognitionManager._onSpeechRecognized.RemoveListener(HandleSpeechRecognized);
                speechRecognitionManager._onStartListening.RemoveListener(OnStartListening);
                speechRecognitionManager._onStopListening.RemoveListener(OnStopListening);
            }

            if (webSocketManager != null)
            {
                webSocketManager.Off("spatial_reference_result");
                webSocketManager.Off("robot_command");
                webSocketManager.Off("error");
                webSocketManager.Off("server_error");
                webSocketManager.Off("processing_status");
            }

            if (LanguageSettings.Instance != null)
            {
                LanguageSettings.Instance.OnLanguageChanged -= OnLanguageChanged;
            }
        }

        private void HandleSpeechRecognized(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return;

            switch (CurrentState)
            {
                case AppState.ShowingResult:
                case AppState.Refining:
                    QueuePendingSpeech(text, isFeedback: true);
                    return;

                case AppState.Processing:
                case AppState.Executing:
                    Log($"Speech ignored in state={CurrentState}: {text}", "yellow");
                    return;

                default:
                    QueuePendingSpeech(text, isFeedback: false);
                    return;
            }
        }

        public bool SendPendingRecognizedSpeech()
        {
            if (string.IsNullOrWhiteSpace(_pendingRecognizedText))
            {
                Log("No pending speech to send.", "yellow");
                return false;
            }

            bool sent;
            if (_pendingIsFeedback)
            {
                sent = OnUserFeedback(_pendingRecognizedText);
            }
            else
            {
                sent = OnUtteranceReceived(_pendingRecognizedText);
            }

            if (sent)
            {
                ClearPendingSpeech();
            }

            return sent;
        }

        public bool OnUtteranceReceived(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return false;

            if (webSocketManager == null || !webSocketManager.IsConnected)
            {
                SetError("Server not connected");
                return false;
            }

            if (spatialContextProvider == null)
            {
                SetError("SpatialContextProvider not assigned");
                return false;
            }

            var request = spatialContextProvider.BuildRequest(text, language);

            int objectCount = request?.objects?.Count ?? 0;
            if (objectCount <= 0)
            {
                SetError("No spatial objects found, request cancelled");
                Log("Request blocked: objects=0", "red");
                return false;
            }

            _lastRequestId = request.request_id;

            SetState(AppState.Processing, "Processing...");
            webSocketManager.Send("spatial_reference_request", request);
            Log($"Request sent: {request.request_id}, objects={objectCount}", "cyan");
            return true;
        }

        public void OnResultReceived(SpatialReferenceResult result)
        {
            if (result == null)
            {
                SetError("Failed to parse result");
                return;
            }

            _lastTargetObjectId = string.IsNullOrWhiteSpace(result.top_candidate_id)
                ? result.selected_object_id
                : result.top_candidate_id;

            // [Agent] LLMの選択理由をログ出力 + UI表示
            string agentReason = null;
            if (result.candidates != null && result.candidates.Count > 0)
                agentReason = result.candidates[0].reasoning ?? result.candidates[0].reason;
            if (string.IsNullOrWhiteSpace(agentReason))
                agentReason = result.reasoning;
            Debug.Log($"[Agent] Selected: {_lastTargetObjectId} | Reason: {agentReason}");
            SpeechRecognitionUIManager.Instance?.ShowAgentMessage($"{agentReason}");

            Debug.Log($"[Agent] Selected \"{_lastTargetObjectId}\". Please confirm.");
            SpeechRecognitionUIManager.Instance?.ShowUserPrompt(
                "Please confirm the highlighted object.\nSay \"Yes\" to continue or \"No\" to choose again.");

            SetState(AppState.ShowingResult, $"Candidate: {_lastTargetObjectId}");
            HighlightTargetForConfirmation(_lastTargetObjectId);
            OnResultUpdated?.Invoke(result);
            Log($"Result received: selected={_lastTargetObjectId}", "green");
        }

        public bool OnUserFeedback(string feedbackUtterance, string objectId = null)
        {
            if (string.IsNullOrWhiteSpace(feedbackUtterance))
            {
                SetError("Feedback utterance is empty");
                return false;
            }

            if (string.IsNullOrWhiteSpace(objectId))
            {
                objectId = _lastTargetObjectId;
            }

            if (webSocketManager == null || !webSocketManager.IsConnected)
            {
                SetError("Server not connected");
                return false;
            }

            if (spatialContextProvider == null)
            {
                SetError("SpatialContextProvider not assigned");
                return false;
            }

            var msg = new ConfirmationInterpretationRequest
            {
                request_id = Guid.NewGuid().ToString(),
                original_request_id = _lastRequestId,
                utterance = new Utterance
                {
                    text = feedbackUtterance,
                    language = language
                },
                confirmed_object_id = objectId,
                action = "pick",
                user_pose = spatialContextProvider.GetUserPose()
            };

            SetState(AppState.Processing, "Interpreting feedback...");
            webSocketManager.Send("confirmation_interpretation_request", msg);
            Log($"Feedback sent: utterance={feedbackUtterance}, object={objectId}", "white");
            return true;
        }

        public void OnRobotCommandReceived(RobotCommand cmd)
        {
            if (cmd == null)
            {
                SetError("Failed to parse robot_command");
                return;
            }

            string status = (cmd.status ?? string.Empty).Trim().ToLowerInvariant();
            bool completed = status == "done" || status == "completed" || status == "finished" || status == "success";
            bool failed = status == "failed" || status == "error" || status == "aborted";

            if (completed)
            {
                SpeechRecognitionUIManager.Instance?.ShowSystemStatus("Execution complete");
                SetState(AppState.Idle, "Done");
            }
            else if (failed)
            {
                string errorMsg = string.IsNullOrWhiteSpace(cmd.message)
                    ? "Robot execution failed"
                    : cmd.message;
                SetError(errorMsg);
            }
            else
            {
                SetState(AppState.Executing, "Robot moving...");
            }

            string actionName = string.IsNullOrWhiteSpace(cmd.action) ? cmd.command : cmd.action;
            string targetObject = string.IsNullOrWhiteSpace(cmd.target_object_id) ? cmd.object_id : cmd.target_object_id;
            Log($"Robot command received: action={actionName}, target={targetObject}, status={cmd.status}, message={cmd.message}", "yellow");
        }

        public void CancelToIdle()
        {
            SetState(AppState.Idle, "Cancelled");
        }

        private void OnProcessingStatusReceived(ProcessingStatus status)
        {
            if (status == null) return;
            Debug.Log($"[ProcessingStatus] stage={status.stage} | {status.message}");
            SpeechRecognitionUIManager.Instance?.ShowSystemStatus(status.message);
        }

        private void OnServerErrorReceived(ServerErrorMessage error)
        {
            if (error == null)
            {
                SetError("Unknown server error");
                return;
            }

            string message = string.IsNullOrWhiteSpace(error.message)
                ? $"Server error: {error.code}"
                : error.message;

            SetError(message);
        }

        private void OnStartListening()
        {
            if (CurrentState == AppState.Idle)
            {
                SetState(AppState.Listening, "Listening...");
            }
        }

        private void OnStopListening()
        {
            if (CurrentState == AppState.Listening)
            {
                SetState(AppState.Idle, "Idle");
            }
        }

        private Coroutine _errorRecoveryCoroutine;

        private void SetError(string message)
        {
            SetState(AppState.Error, message);
            Log(message, "red");

            // エラー表示後、自動的にIdleに戻す
            if (_errorRecoveryCoroutine != null)
                StopCoroutine(_errorRecoveryCoroutine);
            _errorRecoveryCoroutine = StartCoroutine(RecoverFromErrorAfterDelay(3f));
        }

        private IEnumerator RecoverFromErrorAfterDelay(float seconds)
        {
            yield return new WaitForSeconds(seconds);
            if (CurrentState == AppState.Error)
            {
                SetState(AppState.Idle, "Idle");
            }
            _errorRecoveryCoroutine = null;
        }

        private void SetState(AppState next, string statusMessage)
        {
            if (next != AppState.ShowingResult && next != AppState.Refining)
            {
                ClearHighlightedTarget();
            }

            CurrentState = next;
            OnStateChanged?.Invoke(CurrentState);
            OnStatusChanged?.Invoke(statusMessage);

            // SpeechRecognitionUIManager をステートに応じて更新
            // ShowingResult は OnResultReceived 側で上書きするためここでは基本メッセージのみ
            var ui = SpeechRecognitionUIManager.Instance;
            if (ui == null) return;

            switch (next)
            {
                case AppState.Idle:
                    ui.ClearAll();
                    ui.ShowUserPrompt("Please say a command for the robot.");
                    break;
                case AppState.Listening:
                    ui.ShowSystemStatus("Listening...");
                    break;
                case AppState.Processing:
                    ui.ClearResultTexts();
                    ui.ShowSystemStatus(statusMessage);
                    break;
                case AppState.Executing:
                    ui.ShowSystemStatus(statusMessage);
                    break;
                case AppState.Refining:
                    ui.ShowSystemStatus(statusMessage);
                    break;
                case AppState.Error:
                    ui.ShowError(statusMessage);
                    break;
            }
        }

        private void QueuePendingSpeech(string text, bool isFeedback)
        {
            _pendingRecognizedText = text;
            _pendingIsFeedback = isFeedback;

            if (isFeedback)
            {
                SetState(AppState.Refining, "Send your confirmation when you are ready.");
            }
            else
            {
                SetState(AppState.Idle, "Tell the robot what to do, then send your instruction.");
            }

            OnPendingSpeechChanged?.Invoke(true, _pendingRecognizedText, _pendingIsFeedback);
            Log($"Pending speech queued ({(isFeedback ? "confirmation" : "initial")}): {text}", "white");
        }

        public void ClearPendingSpeech()
        {
            _pendingRecognizedText = null;
            _pendingIsFeedback = false;
            OnPendingSpeechChanged?.Invoke(false, string.Empty, false);
        }

        private void HighlightTargetForConfirmation(string objectId)
        {
            ClearHighlightedTarget();

            if (string.IsNullOrWhiteSpace(objectId) || spatialContextProvider == null)
            {
                return;
            }

            SpatialObject targetObject = spatialContextProvider.FindSpatialObject(objectId);
            if (targetObject == null)
            {
                Log($"Highlight target not found: {objectId}", "yellow");
                return;
            }

            targetObject.Highlight();
            _highlightedSpatialObject = targetObject;
        }

        private void ClearHighlightedTarget()
        {
            if (_highlightedSpatialObject == null)
            {
                return;
            }

            _highlightedSpatialObject.Unhighlight();
            _highlightedSpatialObject = null;
        }

        private void Log(string message, string color)
        {
            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.Log($"[AppStateManager] {message}", true, color);
            }
            else
            {
                Debug.Log($"[AppStateManager] {message}");
            }
        }
    }
}
