using System;
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
        [SerializeField] private string language = "ja";
        [SerializeField] private bool autoSubscribeOnEnable = true;

        public AppState CurrentState { get; private set; } = AppState.Idle;

        public event Action<AppState> OnStateChanged;
        public event Action<string> OnStatusChanged;
        public event Action<SpatialReferenceResult> OnResultUpdated;

        private string _lastRequestId;
        private string _lastTargetObjectId;

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
                speechRecognitionManager._onSpeechRecognized.AddListener(OnUtteranceReceived);
                speechRecognitionManager._onStartListening.AddListener(OnStartListening);
                speechRecognitionManager._onStopListening.AddListener(OnStopListening);
            }

            if (webSocketManager != null)
            {
                webSocketManager.On<SpatialReferenceResult>("spatial_reference_result", OnResultReceived);
                webSocketManager.On<RobotCommand>("robot_command", OnRobotCommandReceived);
                webSocketManager.On<ServerErrorMessage>("server_error", OnServerErrorReceived);
            }
        }

        public void Unsubscribe()
        {
            if (speechRecognitionManager != null)
            {
                speechRecognitionManager._onSpeechRecognized.RemoveListener(OnUtteranceReceived);
                speechRecognitionManager._onStartListening.RemoveListener(OnStartListening);
                speechRecognitionManager._onStopListening.RemoveListener(OnStopListening);
            }

            if (webSocketManager != null)
            {
                webSocketManager.Off("spatial_reference_result");
                webSocketManager.Off("robot_command");
                webSocketManager.Off("server_error");
            }
        }

        public void OnUtteranceReceived(string text)
        {
            if (string.IsNullOrWhiteSpace(text)) return;

            if (webSocketManager == null || !webSocketManager.IsConnected)
            {
                SetError("サーバー未接続です");
                return;
            }

            if (spatialContextProvider == null)
            {
                SetError("SpatialContextProvider が未設定です");
                return;
            }

            var request = spatialContextProvider.BuildRequest(text, language);
            _lastRequestId = request.request_id;

            SetState(AppState.Processing, "推論中...");
            webSocketManager.Send("spatial_reference_request", request);
            Log($"Request sent: {request.request_id}", "cyan");
        }

        public void OnResultReceived(SpatialReferenceResult result)
        {
            if (result == null)
            {
                SetError("結果メッセージの解析に失敗しました");
                return;
            }

            _lastTargetObjectId = result.selected_object_id;
            SetState(AppState.ShowingResult, $"候補: {_lastTargetObjectId}");
            OnResultUpdated?.Invoke(result);
            Log($"Result received: selected={_lastTargetObjectId}", "green");
        }

        public void OnUserConfirmed(string objectId)
        {
            if (string.IsNullOrWhiteSpace(objectId))
            {
                objectId = _lastTargetObjectId;
            }

            if (string.IsNullOrWhiteSpace(objectId))
            {
                SetError("確認対象の object_id がありません");
                return;
            }

            var msg = new ConfirmationMessage
            {
                request_id = Guid.NewGuid().ToString(),
                original_request_id = _lastRequestId,
                confirmed_object_id = objectId,
                action = "pick"
            };

            SetState(AppState.Executing, "ロボット実行中...");
            webSocketManager.Send("confirmation", msg);
            Log($"Confirmation sent: object={objectId}", "white");
        }

        public void OnUserRefined(string refinementText)
        {
            if (string.IsNullOrWhiteSpace(refinementText))
            {
                SetError("修正発話が空です");
                return;
            }

            if (spatialContextProvider == null)
            {
                SetError("SpatialContextProvider が未設定です");
                return;
            }

            var msg = new RefinementRequest
            {
                request_id = Guid.NewGuid().ToString(),
                original_request_id = _lastRequestId,
                utterance = new Utterance
                {
                    text = refinementText,
                    language = language
                },
                user_pose = spatialContextProvider.GetUserPose(),
                previous_target = _lastTargetObjectId
            };

            SetState(AppState.Refining, "修正指示を送信中...");
            webSocketManager.Send("refinement_request", msg);
            SetState(AppState.Processing, "再推論中...");
            Log("Refinement request sent", "white");
        }

        public void OnRobotCommandReceived(RobotCommand cmd)
        {
            if (cmd == null)
            {
                SetError("robot_command の解析に失敗しました");
                return;
            }

            string status = (cmd.status ?? string.Empty).Trim().ToLowerInvariant();
            bool completed = status == "done" || status == "completed" || status == "finished" || status == "success";

            if (completed)
            {
                SetState(AppState.Idle, "完了");
            }
            else
            {
                SetState(AppState.Executing, $"ロボット状態: {cmd.status}");
            }

            Log($"Robot command received: {cmd.command} ({cmd.status})", "yellow");
        }

        public void CancelToIdle()
        {
            SetState(AppState.Idle, "キャンセル");
        }

        private void OnServerErrorReceived(ServerErrorMessage error)
        {
            if (error == null)
            {
                SetError("不明なサーバーエラー");
                return;
            }

            string message = string.IsNullOrWhiteSpace(error.message)
                ? $"サーバーエラー: {error.code}"
                : error.message;

            SetError(message);
        }

        private void OnStartListening()
        {
            if (CurrentState == AppState.Idle)
            {
                SetState(AppState.Listening, "聞いています...");
            }
        }

        private void OnStopListening()
        {
            if (CurrentState == AppState.Listening)
            {
                SetState(AppState.Idle, "待機中");
            }
        }

        private void SetError(string message)
        {
            SetState(AppState.Error, message);
            Log(message, "red");
        }

        private void SetState(AppState next, string statusMessage)
        {
            CurrentState = next;
            OnStateChanged?.Invoke(CurrentState);
            OnStatusChanged?.Invoke(statusMessage);
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