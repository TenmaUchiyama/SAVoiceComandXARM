using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using SA_XARM.Calibration;
using SA_XARM.SpatialRef.Spatial;

namespace SA_XARM.Network.Websocket
{
    [Serializable]
    public class PcDebugPersistentListRequest
    {
        public string request_id;
        public bool recursive;
    }

    [Serializable]
    public class PcDebugPersistentListResponse
    {
        public string request_id;
        public bool success;
        public string base_path;
        public List<string> files;
        public List<string> directories;
        public string error;
    }

    [Serializable]
    public class PcDebugReadJsonRequest
    {
        public string request_id;
        public string relative_path;
    }

    [Serializable]
    public class PcDebugReadJsonResponse
    {
        public string request_id;
        public bool success;
        public string relative_path;
        public string content;
        public string error;
    }

    [Serializable]
    public class PcDebugCalibrationRequest
    {
        public string request_id;
        public string action;
    }

    [Serializable]
    public class PcDebugCalibrationResponse
    {
        public string request_id;
        public bool success;
        public string action;
        public string message;
        public QRGridToolDebugStatus qr_grid_tool_status;
        public string error;
    }

    public class PCDebuggerWebSocket : MonoBehaviour
    {
        [Header("WebSocket Event IDs")]
        [SerializeField] private string listRequestEventId = "pc_debug_persistent_list_request";
        [SerializeField] private string listResponseEventId = "pc_debug_persistent_list_response";
        [SerializeField] private string readJsonRequestEventId = "pc_debug_read_json_request";
        [SerializeField] private string readJsonResponseEventId = "pc_debug_read_json_response";
        [SerializeField] private string calibrationRequestEventId = "pc_debug_calibration_request";
        [SerializeField] private string calibrationResponseEventId = "pc_debug_calibration_response";

        [Header("Settings")]
        [SerializeField] private bool autoSubscribeOnEnable = true;

        /// <summary>
        /// デバッグ系イベントは DebugWebSocketClient (port 8765) を使用する。
        /// WebSocketManager (port 8080/spatial) とは独立した接続。
        /// </summary>
        private DebugWebSocketClient _debugClient;

        private void Start()
        {
            SafeLog("[PCDebuggerWS] Initialized.");
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
            _debugClient = ResolveClient();
            if (_debugClient == null)
            {
                SafeLogError("[PCDebuggerWS] DebugWebSocketClient is not available.");
                return;
            }

            _debugClient.On<PcDebugPersistentListRequest>(listRequestEventId, OnListRequestReceived);
            _debugClient.On<PcDebugReadJsonRequest>(readJsonRequestEventId, OnReadJsonRequestReceived);
            _debugClient.On<PcDebugCalibrationRequest>(calibrationRequestEventId, OnCalibrationRequestReceived);
            SafeLog("[PCDebuggerWS] Subscribed request handlers (via DebugWebSocketClient).", "cyan");
        }

        public void Unsubscribe()
        {
            var client = ResolveClient();
            if (client == null) return;

            client.Off(listRequestEventId);
            client.Off(readJsonRequestEventId);
            client.Off(calibrationRequestEventId);
        }

        private void OnCalibrationRequestReceived(PcDebugCalibrationRequest request)
        {
            var response = new PcDebugCalibrationResponse
            {
                request_id = request?.request_id,
                success = false,
                action = request?.action,
                message = null,
                qr_grid_tool_status = null,
                error = null
            };

            try
            {
                string action = (request?.action ?? string.Empty).Trim().ToLowerInvariant();
                if (string.IsNullOrWhiteSpace(action))
                {
                    response.error = "action is required.";
                    Send(calibrationResponseEventId, response);
                    return;
                }

                QRGridTool gridTool = FindObjectOfType<QRGridTool>(true);
                QRGridCalibrator legacyCalibrator = FindObjectOfType<QRGridCalibrator>(true);
                GridObjectRestorer legacyRestorer = FindObjectOfType<GridObjectRestorer>(true);

                switch (action)
                {
                    case "teach":
                    case "mode_teach":
                    case "start_calibration":
                        if (gridTool == null)
                        {
                            response.error = "QRGridTool not found in scene.";
                            break;
                        }
                        gridTool.SetTeachModeFromRemote();
                        response.success = true;
                        response.message = "Mode set to TEACH.";
                        break;

                    case "restore":
                    case "mode_restore":
                        if (gridTool == null)
                        {
                            response.error = "QRGridTool not found in scene.";
                            break;
                        }
                        gridTool.SetRestoreModeFromRemote();
                        response.success = true;
                        response.message = "Mode set to RESTORE.";
                        break;

                    case "record":
                    case "space":
                    case "next":
                        if (gridTool != null)
                        {
                            gridTool.TriggerSpaceActionFromRemote();
                            response.success = true;
                            response.message = "Executed SPACE action on QRGridTool.";
                        }
                        else if (legacyCalibrator != null)
                        {
                            legacyCalibrator.RecordCurrentPoint();
                            response.success = true;
                            response.message = "Recorded one point on QRGridCalibrator.";
                        }
                        else if (legacyRestorer != null)
                        {
                            legacyRestorer.TryRestoreObjects();
                            response.success = true;
                            response.message = "Triggered restore on GridObjectRestorer.";
                        }
                        else
                        {
                            response.error = "No calibration component found (QRGridTool/QRGridCalibrator/GridObjectRestorer).";
                        }
                        break;

                    case "record_robot":
                    case "robot":
                    case "l":
                        if (gridTool == null)
                        {
                            response.error = "QRGridTool not found in scene.";
                            break;
                        }
                        gridTool.TriggerRecordRobotFromRemote();
                        response.success = true;
                        response.message = "Recorded robot point.";
                        break;

                    case "restore_local":
                    case "apply_restore":
                        if (gridTool != null)
                        {
                            gridTool.TryRestoreFromLocalFiles();
                            response.success = true;
                            response.message = "Triggered local restore on QRGridTool.";
                        }
                        else if (legacyRestorer != null)
                        {
                            legacyRestorer.TryRestoreObjects();
                            response.success = true;
                            response.message = "Triggered restore on GridObjectRestorer.";
                        }
                        else
                        {
                            response.error = "No restorer component found.";
                        }
                        break;

                    case "clear":
                    case "reset":
                        if (gridTool == null)
                        {
                            response.error = "QRGridTool not found in scene.";
                            break;
                        }
                        gridTool.ClearAllFromRemote();
                        response.success = true;
                        response.message = "Cleared QRGridTool state.";
                        break;

                    case "grid_show":
                    case "show_grid":
                    {
                        ObjectRegistry registry = FindObjectOfType<ObjectRegistry>(true);
                        if (registry == null)
                        {
                            response.error = "ObjectRegistry not found in scene.";
                            break;
                        }
                        registry.SetVisualAll(true);
                        response.success = true;
                        response.message = "Grid visual shown.";
                        break;
                    }

                    case "grid_hide":
                    case "hide_grid":
                    {
                        ObjectRegistry registry = FindObjectOfType<ObjectRegistry>(true);
                        if (registry == null)
                        {
                            response.error = "ObjectRegistry not found in scene.";
                            break;
                        }
                        registry.SetVisualAll(false);
                        response.success = true;
                        response.message = "Grid visual hidden.";
                        break;
                    }

                    case "status":
                        response.success = true;
                        response.message = "Status collected.";
                        break;

                    default:
                        response.error = $"unknown action: {action}";
                        break;
                }

                if (gridTool != null)
                {
                    response.qr_grid_tool_status = gridTool.GetDebugStatus();
                }
            }
            catch (Exception ex)
            {
                response.error = ex.Message;
                SafeLogError($"[PCDebuggerWS] Calibration command failed: {ex.Message}");
            }

            Send(calibrationResponseEventId, response);
        }

        private void OnListRequestReceived(PcDebugPersistentListRequest request)
        {
            var response = new PcDebugPersistentListResponse
            {
                request_id = request?.request_id,
                success = false,
                files = new List<string>(),
                directories = new List<string>(),
                base_path = Application.persistentDataPath,
                error = null
            };

            try
            {
                string basePath = Application.persistentDataPath;
                bool recursive = request != null && request.recursive;
                SearchOption searchOption = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;

                foreach (string dirPath in Directory.GetDirectories(basePath, "*", searchOption))
                {
                    response.directories.Add(ToRelativePath(basePath, dirPath));
                }

                foreach (string filePath in Directory.GetFiles(basePath, "*", searchOption))
                {
                    response.files.Add(ToRelativePath(basePath, filePath));
                }

                response.success = true;
            }
            catch (Exception ex)
            {
                response.error = ex.Message;
                SafeLogError($"[PCDebuggerWS] Failed to list persistentDataPath: {ex.Message}");
            }

            Send(listResponseEventId, response);
        }

        private void OnReadJsonRequestReceived(PcDebugReadJsonRequest request)
        {
            var response = new PcDebugReadJsonResponse
            {
                request_id = request?.request_id,
                success = false,
                relative_path = request?.relative_path,
                content = null,
                error = null
            };

            if (request == null || string.IsNullOrWhiteSpace(request.relative_path))
            {
                response.error = "relative_path is required.";
                Send(readJsonResponseEventId, response);
                return;
            }

            try
            {
                if (!TryResolveSafePath(Application.persistentDataPath, request.relative_path, out string fullPath, out string normalizedRelativePath, out string pathError))
                {
                    response.error = pathError;
                    Send(readJsonResponseEventId, response);
                    return;
                }

                if (!normalizedRelativePath.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
                {
                    response.error = "Only .json files are supported.";
                    Send(readJsonResponseEventId, response);
                    return;
                }

                if (!File.Exists(fullPath))
                {
                    response.error = "File not found.";
                    Send(readJsonResponseEventId, response);
                    return;
                }

                response.relative_path = normalizedRelativePath;
                response.content = File.ReadAllText(fullPath);
                response.success = true;
            }
            catch (Exception ex)
            {
                response.error = ex.Message;
                SafeLogError($"[PCDebuggerWS] Failed to read json file: {ex.Message}");
            }

            Send(readJsonResponseEventId, response);
        }

        private void Send<T>(string eventId, T payload)
        {
            var client = ResolveClient();
            if (client == null || !client.IsConnected)
            {
                SafeLogError($"[PCDebuggerWS] Cannot send '{eventId}' because DebugWebSocket is not connected.");
                return;
            }

            client.Send(eventId, payload);
        }

        private DebugWebSocketClient ResolveClient()
        {
            if (_debugClient != null) return _debugClient;
            _debugClient = DebugWebSocketClient.Instance;
            return _debugClient;
        }

        private static string ToRelativePath(string basePath, string targetPath)
        {
            string baseFullPath = Path.GetFullPath(basePath);
            if (!baseFullPath.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal))
            {
                baseFullPath += Path.DirectorySeparatorChar;
            }

            Uri baseUri = new Uri(baseFullPath);
            Uri targetUri = new Uri(Path.GetFullPath(targetPath));
            string relative = Uri.UnescapeDataString(baseUri.MakeRelativeUri(targetUri).ToString());
            return relative.Replace('\\', '/');
        }

        private static bool TryResolveSafePath(string basePath, string relativePath, out string fullPath, out string normalizedRelativePath, out string error)
        {
            fullPath = null;
            normalizedRelativePath = null;
            error = null;

            string sanitized = relativePath.Replace('\\', '/').Trim();
            while (sanitized.StartsWith("/", StringComparison.Ordinal))
            {
                sanitized = sanitized.Substring(1);
            }

            if (string.IsNullOrWhiteSpace(sanitized))
            {
                error = "relative_path is empty.";
                return false;
            }

            if (Path.IsPathRooted(sanitized))
            {
                error = "absolute path is not allowed.";
                return false;
            }

            string baseFullPath = Path.GetFullPath(basePath);
            string candidatePath = Path.GetFullPath(Path.Combine(baseFullPath, sanitized));

            string baseWithSep = baseFullPath.EndsWith(Path.DirectorySeparatorChar.ToString(), StringComparison.Ordinal)
                ? baseFullPath
                : baseFullPath + Path.DirectorySeparatorChar;

            bool isInside = candidatePath.StartsWith(baseWithSep, StringComparison.OrdinalIgnoreCase)
                || string.Equals(candidatePath, baseFullPath, StringComparison.OrdinalIgnoreCase);

            if (!isInside)
            {
                error = "path traversal is not allowed.";
                return false;
            }

            fullPath = candidatePath;
            normalizedRelativePath = ToRelativePath(baseFullPath, candidatePath);
            return true;
        }

        private static void SafeLog(string message, string color = "white")
        {
            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.Log(message, true, color);
                return;
            }

            Debug.Log(message);
        }

        private static void SafeLogError(string message)
        {
            if (SpatialDebugLog.Instance != null)
            {
                SpatialDebugLog.Instance.LogError(message, true);
                return;
            }

            Debug.LogError(message);
        }
    }
}